from typing import List, Dict, Union
import pandas as pd
import boto3
import pdb
import yaml
import structlog
from src.schemas import OcrDataReturn, CleanMetaReturn, WorkoutDataReturn
from src.schemas import CustomError, CellData

# Load config file values
with open("config/config.yaml", "r") as f:
    config_data = yaml.load(f, Loader=yaml.FullLoader)

ACCESS_KEY = config_data["AWS_ACCESS_KEY_ID"]
SECRET_KEY = config_data["AWS_SECRET_ACCESS_KEY"]

client = boto3.client(
    "textract",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name="us-east-1",
)

log = structlog.get_logger()


def hit_textract_api(erg_image_bytearray):
    try:
        return client.analyze_document(
            Document={"Bytes": erg_image_bytearray}, FeatureTypes=["TABLES"]
        )
    except Exception as e:
        raise CustomError(status_code=500, message=f"hit_textract_api failed, {e}")
        


# Extract Workout Data - Create List[dict] with table data: row, column, text, text_id
def create_word_index(image_raw_response: dict) -> dict:
    # pdb.set_trace()
    try:
        # create dict {word_id : word_text}
        word_blocks: List[dict] = [
            block
            for block in image_raw_response["Blocks"]
            if block["BlockType"] == "WORD"
        ]
        word_index = {}
        for block in word_blocks:
            word_index[block["Id"]] = block["Text"]
        return word_index
    except Exception as e:
        raise CustomError(status_code=500, message=f"create_word_index failed, {e}")


def remove_blocks_before_time(word_index, cell_blocks) -> dict:
    # DELETE cells before 'time'
    # get time_id
    for key, value in word_index.items():
        if value == "time":
            time_id = key
            break
    # find index of block in cell_blocks with text == 'time'
    time_index = 0
    time_row_index = 0
    for block in cell_blocks:
        # if cell empty and before "time" or populated and before 'time'
        if (not "Relationships" in block.keys()) or (
            not time_id in block["Relationships"][0]["Ids"]
        ):
            log.debug("remove", row=block["RowIndex"], col=block["ColumnIndex"])
            time_index += 1
        else:
            time_row_index = block["RowIndex"]
            break
    # if time not in any cells
    if not time_row_index:
        return cell_blocks, 1
    # remove  all blocks before 'time' block
    return cell_blocks[time_index:], time_row_index


def process_merged_cols(cell_blocks, time_row_index, word_index):
    table_data = []
    # create a list of all the ids for words corresponding to workout data (no col heads)
    block_text_ids = []
    for block in cell_blocks:
        # for rows with data (i.e. not column headings)
        if not block["RowIndex"] == time_row_index:
            try:
                for id in block["Relationships"][0]["Ids"]:
                    block_text_ids.append(id)
            except KeyError:
                continue
    # Create first row - will become column headings in future function
    for c in range(6):
        cell_data = {
            "row": 1,
            "col": c + 1,
            "text": ["time"],
            "text_id": [""],
        }
        table_data.append(cell_data)
    # find num rows (last rowindex - 'time' rowIndex)
    num_rows = cell_blocks[-1]["RowIndex"] - time_row_index
    # determin if HR is in data by checking if 5th word is int (i.e. HR) or str(time row2)
    hr_present = True
    try:
        int(word_index[block_text_ids[4]])
    except ValueError:
        hr_present = False

    i = 0
    for r in range(1, num_rows):  # fm 1 because first row is blank
        for c in range(1, 6):  # cols 1-5
            # add empty HR cell - no HR data
            if not hr_present and c == 5:
                cell_data = {
                    "row": r,
                    "col": 5,
                    "text": [""],
                }
            else:
                cell_data = {
                    "row": r,
                    "col": c,
                    "text": [word_index[block_text_ids[i]]],
                    "text_id": [block_text_ids[i]],
                }
                i += 1
            table_data.append(cell_data)
    return table_data


def add_empty_cell_if_needed(table_data, block) -> Union[dict, bool]:
    # if previous block didn't correct empty cell, add empty entry - see FIX  below
    # fix (i.e. not needed) would apply if SR had been lumped in with split or HR lumped in with SR
    # if fixed: when processing split/SR, unmerged SR/HR cell would have been added 
    if not (
        table_data[-1]["row"] == block["RowIndex"]
        and table_data[-1]["col"] == block["ColumnIndex"]
    ):
        cell_data = {
            "row": block["RowIndex"],
            "col": block["ColumnIndex"],
            "text": [""],
        }
        return cell_data
    return False


def extract_table_data(image_raw_response: dict, word_index: dict) -> List[CellData]:
    try:
        # create list of cell  blocks
        cell_blocks: List[dict] = [
            block
            for block in image_raw_response["Blocks"]
            if block["BlockType"] == "CELL"
        ]
        cell_blocks, time_row_index = remove_blocks_before_time(word_index, cell_blocks)
        log.debug(f"cell blocks len: {len(cell_blocks)}")

        # CHECK number of columns
        num_cols = cell_blocks[-1]["ColumnIndex"]
        log.debug(f"num cols: {num_cols}")

        if not 1 < num_cols < 7:
            raise CustomError(status_code=500, message="extract_table_data failed, invalid column count")
        # if num cols is 6 check if last two cols are empty and delete them if they are
        if num_cols == 6:
            # create list of all col 5 and 6 cells
            col56 = [block for block in cell_blocks if block["ColumnIndex"] in [5, 6]]
            content = False
            # check if empty
            for block in col56:
                if "Relationships" in block.keys():
                    content = True
            if not content:
                cell_blocks = [
                    block for block in cell_blocks if block["ColumnIndex"] not in [5, 6]
                ]
                num_cols = 4

        # if num cols is 2 or three seperate merged cols:
        if num_cols < 4:
            log.info("Merged cols detected")
            table_data = process_merged_cols(
                cell_blocks, time_row_index, word_index
            )  # TODO: come back to add HR
        else: #Num cols = 4 or 5 => most common case
            table_data = []
            for block in cell_blocks:
                #  if cell is empty, add empty entry.
                if not "Relationships" in block.keys():
                    cell_data = add_empty_cell_if_needed(table_data, block)
                    if cell_data:
                        table_data.append(cell_data)
                # deal with cells in columns 1-5 that have content
                elif "Relationships" in block.keys():
                    cell_data = {"row": None, "col": None, "text": [], "text_ids": []}
                    cell_data["row"] = block["RowIndex"]
                    cell_data["col"] = block["ColumnIndex"]
                    for word_id in block["Relationships"][0]["Ids"]:
                        cell_data["text_ids"].append(word_id)
                    for word_id in cell_data["text_ids"]:
                        cell_data["text"].append(word_index[word_id])
                    table_data.append(cell_data)
                    # FIX for when stroke rate gets lumped in with split in Col3 but still recognized as two words
                    if block["ColumnIndex"] == 3 and len(cell_data["text_ids"]) > 1:
                        table_data.append(
                            {
                                "row": block["RowIndex"],
                                "col": 4,
                                "text": [word_index[cell_data["text_ids"][-1]]],
                                "text_id": [cell_data["text_ids"][-1]],
                            }
                        )

                    # FIX HR gets lumped in with SR in col4 either as two words or as one
                    if block["ColumnIndex"] == 4 and (
                        len(cell_data["text_ids"]) > 1
                        or 4 < len(cell_data["text"][0])
                    ):
                        # delete most recent cell entry in table_data - it contains the merged SR/HR data
                        del table_data[-1]
                        # SubFix: Split, SR and HR all lumped together as seperate words *rare
                        # pdb.set_trace()
                        if len(cell_data["text"]) == 3 and not table_data[-1]['text']:
                            # split cell currently an empty cell. Fill content
                            table_data[-1]['text_ids'] = [cell_data['text_ids'][0]]
                            table_data[-1]['text'] = [cell_data['text'][0]]
                            del cell_data['text_ids'][0]
                            del cell_data['text'][0]
                        #Subfix: Split, SR, HR lumped together as one word with spaces *rare
                        if len(cell_data['text'][0]) > 7 and not table_data[-1]['text'][0]:
                            text = cell_data['text'][0].strip() 
                            table_data[-1]['text_ids'] = ['fm SR']
                            table_data[-1]['text'] = [text[:6]]
                            cell_data['text'][0] = text[6:]
                        # isolate SR and HR data
                        if len(cell_data["text_ids"]) > 1:
                            sr = cell_data["text"][0]
                            hr = cell_data["text"][1]
                            sr_text_id = cell_data["text_ids"][0]
                            hr_text_id = ["from SR"]  # for debugging
                        else:
                            sr = cell_data["text"][0][:2]
                            hr = cell_data["text"][0][2:].strip()
                            sr_text_id = ["altered - SRHR split"]  # for debugging
                            hr_text_id = ["from SR"]  # for debugging
                        table_data.append(
                            {
                                "row": block["RowIndex"],
                                "col": 4,
                                "text": [sr],
                                "text_id": sr_text_id,
                            }
                        )
                        table_data.append(
                            {
                                "row": block["RowIndex"],
                                "col": 5,
                                "text": [hr],
                                "text_id": hr_text_id,
                            }
                        )
                        # add HR column heading if missing
                        if table_data[4]["row"] == 2:
                            hr_head = {
                                "row": table_data[0]["row"],
                                "col": 5,
                                "text": ["hr"],
                                "text_id": ["text hard coded"],
                            }

                            table_data.insert(4, hr_head)
                    # FIX SR gets lumped in with HR in col5 either as two words or as one (* assumes len(sr)==2, len(hr)==3)
                    if block["ColumnIndex"] == 5 and (
                        len(cell_data["text_ids"]) > 1
                        or 4 < len(cell_data["text"][0]) < 7
                    ):
                        # cell most recently added to table_data will be missing text - populate it from this HR cell
                        if len(cell_data["text_ids"]) > 1:
                            table_data[-2]["text"][0] = cell_data["text"][0]
                            table_data[-2]["text_ids"] = [
                                "from HR"
                            ]  # not neccessary but helpful for debugging
                            del table_data[-1]["text"][0]
                            del table_data[-1]["text_ids"][
                                0
                            ]  # not neccessary but cleaner
                        else:
                            sr = cell_data["text"][0][:2]
                            hr = cell_data["text"][0][2:].strip()
                            table_data[-2]["text"][0] = sr
                            table_data[-2]["text_ids"] = [
                                "from HR"
                            ]  # not neccessary - helpful for debugging
                            table_data[-1]["text"][0] = hr
                            table_data[-1]["text_ids"] = [
                                "altered - SRHR split"
                            ]  # not neccessary - helpful for debugging
            # Add HR col - all empty
            if num_cols == 4 and table_data[-1]["col"] == 4:
                for i in range(len(table_data) // 4):
                    hr_index = (i + 1) * 5 - 1
                    first_data_row = table_data[0]["row"]
                    cell_data = {
                        "row": first_data_row + i,
                        "col": 5,
                        "text": [""],
                    }
                    table_data.insert(hr_index, cell_data)
        return table_data
    except Exception as e:
        raise CustomError(status_code=500, message=f"extract_table_data failed, {e}")


# clean workout data - replace column labels & change "," for "."
def clean_table_data(table_data: List[dict]):
    try:
        # remove all cells before 'time'
        while "time" not in table_data[0]["text"]:
            del table_data[0]
        # add col headings
        table_data[0]["text"] = ["time"]
        table_data[1]["text"] = ["meter"]
        table_data[2]["text"] = ["split"]
        table_data[3]["text"] = ["sr"]
        table_data[4]["text"] = ["hr"]
        for cell in table_data:
            for word in cell["text"]:
                if "," in word:
                    word_index = cell["text"].index(word)
                    cell["text"][word_index] = word.replace(",", ".")
        return table_data
    except Exception as e:
        raise CustomError(status_code=500, message=f"clean_table_data failed, {e}")


# view workout data - visual only
def compile_workout_data(wo_clean: List[dict], ints_var:bool) -> WorkoutDataReturn:
    try:
        col_head_row = wo_clean[0]["row"]
        wo_dict = {"time": [], "meter": [], "split": [], "sr": [], "hr": []}
        rest_info = {"time": [], "meter":[]}
        for cell in wo_clean:
            if cell["row"] > col_head_row:
                if cell["col"] == 1:
                    wo_dict["time"].append(cell["text"][0])
                    if ints_var and len(cell['text']) == 2:
                        rest_info['time'].append(cell["text"][1])
                elif cell["col"] == 2:
                    wo_dict["meter"].append(cell["text"][0])
                    if ints_var and len(cell['text']) == 2:
                        rest_info['meter'].append(cell["text"][1])
                elif cell["col"] == 3:
                    wo_dict["split"].append(cell["text"][0])
                elif cell["col"] == 4:
                    wo_dict["sr"].append(cell["text"][0])
                elif cell["col"] == 5:
                    wo_dict["hr"].append(cell["text"][0])
        # delete rest row - interval  workouts show # meters rowed during rest time
        if wo_dict["meter"][-1] and not wo_dict["time"][-1]:
            for lst in wo_dict.values():
                del lst[-1]
        return WorkoutDataReturn(time=wo_dict["time"], meter=wo_dict['meter'], split=wo_dict['split'], sr=wo_dict['sr'], hr=wo_dict['hr'])
    except Exception as e:
        raise CustomError(status_code=500, message="compile_workout_data failed, invalid column count")


# extract raw metadata
def extract_metadata(word_index: dict, image_raw_response: dict) -> List[str]:
    raw_meta = []
    line_blocks: List[dict] = [
        block for block in image_raw_response["Blocks"] if block["BlockType"] == "LINE"
    ]
    # find id for word 'time' - beginning of table
    for id, word in word_index.items():
        if word == "time":
            time_id = id
            break
    for block in line_blocks:
        if time_id in block["Relationships"][0]["Ids"]:
            break
        else:
            raw_meta.append(block["Text"])
    return raw_meta


# clean metadata
def clean_metadata(
    raw_meta: list,
) -> CleanMetaReturn:  # actually returning dict right now
    # Delete everything before wo_name
    meta = raw_meta
    try:
        view_detail_idx = [
            i
            for i, item in enumerate(raw_meta)
            if "View" in item or "Detail" in item or "Verification:" in item
        ][-1]
        meta = raw_meta[view_detail_idx + 1 :]
    except:
        pass
    for i in range(len(meta)):
        try:
            meta[i] = meta[i].replace(",", ".")
        except:
            pass
    # pdb.set_trace()
    if 2 <= len(meta) <= 3:
        meta_dict = {"wo_name": meta[0], "wo_date": meta[1]}
    elif len(meta) >= 4:
        meta_dict = {
            "wo_name": meta[0],
            "total_type": meta[1],
            "wo_date": meta[2],
            "total_val": meta[3],
        }
    else:  # catching other scenarios, a patch fix
        meta_combo_string = ""
        for i in range(len(meta)):
            meta_combo_string += meta[i] + " "
        meta_dict = {"wo_name": meta_combo_string, "wo_date": ""}
    return meta_dict


def process_raw_ocr(raw_response: dict, photo_hash: str, ints_var:bool) -> OcrDataReturn:
    # pdb.set_trace()
    word_index = create_word_index(raw_response)
    table_data = extract_table_data(raw_response, word_index)
    log.debug("Table data: ", data=table_data)
    table_data_clean = clean_table_data(table_data)
    log.debug("table_data_clean: ", data=table_data_clean)
    #current 
    # Process variable interval workouts when rest info is merged with row above
    rest_info = {'time': [], 'meter': []}
    if ints_var: 
        rest_info, merged_rows = get_rest_info_fm_merged_rows(table_data_clean)
    workout_data = compile_workout_data(table_data_clean, ints_var)
    # Process variable interval workouts when rest info has its own row 
    if ints_var and not merged_rows:
        log.debug("workout_data pre-varInst adjusted: ", data=workout_data)
        workout_data, rest_info = process_variable_intervals_distinct_rows(workout_data)
    
    #Fix common issues with HR data - fm interval workouts where average HR isn't calculated bt C2Erg
    # Remove empty entries in HR list - assumes time has correct number of entries
    if len(workout_data.hr) > len(workout_data.time):
        workout_data.hr = [h for h in workout_data.hr if h]
    # find and add average 
    if len(workout_data.hr) == len(workout_data.time) - 1: 
        av_hr = int(sum(int(h) for h in workout_data.hr)/len(workout_data.hr))
        workout_data.hr.insert(0,av_hr) 
    # only summary row processed
    if len(workout_data.time) == 1: 
        workout_data = non_table_processing(word_index)

    log.debug("workout_data: ", data=workout_data)

    raw_meta = extract_metadata(word_index, raw_response)
    log.debug("raw_meta: ", data=raw_meta)
    clean_meta = clean_metadata(raw_meta)
    log.debug("Variable Intervals rest info", data=rest_info)
    try: 
        workout_df = pd.DataFrame(workout_data)
        meta_df = pd.DataFrame([clean_meta])
        # Print Pretty
        log.debug("Metadata Pretty Print", data=meta_df)
        log.debug("Workout Data Pretty Print", data=workout_df)
    except:
        pass

    processed_data = OcrDataReturn(
        workout_meta=clean_meta, workout_data=workout_data, photo_hash=[photo_hash], rest_info=rest_info
    )
    return processed_data

def get_rest_info_fm_merged_rows(wo_clean) -> dict:
    try:
        merged_rows = False
        rest_info = {'time': [], 'meter': []}
        col_head_row = wo_clean[0]["row"]
        for cell in wo_clean:
            if cell["row"] > col_head_row:
                if cell["col"] == 1 and len(cell['text']) == 2:
                    merged_rows = True 
                    rest_info['time'].append(cell["text"][1])
                elif cell["col"] == 2 and len(cell['text']) == 2:
                    rest_info['meter'].append(cell["text"][1])
        return rest_info, merged_rows 
    except Exception as e:
        raise CustomError(status_code=500, message=f"get_rest_info_fm_merged_rows failed, {e}")

#current
def process_variable_intervals_distinct_rows(workout_data:WorkoutDataReturn):
    """
    Receives workout data (example below)
        1. rest as its own row
        {'time': ['24:00.0', '8:00.0', 'r:00', '8:00.0', 'H:00', '4:00.0', 'P:00', '4:00.0', 'F:00'], 
        'meter': ['5602', '1826', '0', '1851', '0', '940', '0', '985', '0'], 
        'split': ['2:08.5', '2:11.4', '', '2:09.6', '', '2:07.6', '', '2:01.8', ''], 
        'sr': ['21', '18', '', '20', '', '22', '', '24', ''], 
        'hr': ['', '', '', '', '', '', '', '', '']}

    Create a dict of rest info e.g. {'time':['r1:00', 'r1:00'], 'meter':[23, 43]}
    Also, remove rest info and extra black spaces from workout data 
    """
    rest_info = {}
    for key in workout_data.keys():
        if key == 'time' or key == 'meter':
            rest_info[key] = (workout_data[key][2::2])
        workout_data[key] = workout_data[key][:2]+workout_data[key][3::2]

    return workout_data, rest_info


def clean_wordlist_for_non_table_extraction(word_index):
    words = list(word_index.values())
    #clean data, get rid of commas 
    words_clean = [w.replace(',', '.') for w in words]
    words_split = []
    for w in words_clean:
        words_split.extend(w.split())
    return words_split

def non_table_processing(word_index:dict):
    """
    This exists for the case where of interval workouts that have no average HR 
    and where my other OCR only extracted the summary row of data. Oddly specific 
    but a common kind of workout, especially for me. 
    This function is a hack in a lot of ways and makes a lot of assumptions. 
    Certainly it can be improved but I'm hoping it'll be good enough for most cases
    """
    words = clean_wordlist_for_non_table_extraction(word_index)
    log.debug("OCR Words", data=words)
    # delete all data before 'time' and after(including) rest meters 
    for i in range(len(words)):
        if words[i] == 'time':
            time_idx = i
        # could use more robus regex expression here
        elif words[i][0] == 'r': 
            rest_meters_index = i
    relevant_data = words[time_idx:rest_meters_index]
    # delete all data before summary row time data
    for i in range(len(relevant_data)):
        try:
            int(relevant_data[i])
            summary_time_idx = i - 1
            relevant_data = relevant_data[summary_time_idx:]
            break 
        except:
            continue 
    # insert placeholder hr 
    relevant_data.insert(4, 'hrholder')
    log.debug('Relevant raw data', data=relevant_data)

    # create lists of 
    time = relevant_data[0::5]
    meter = relevant_data[1::5]
    split = relevant_data[2::5]
    sr = relevant_data[3::5]
    hr = relevant_data[4::5]
    # fix HR stand in
    del hr[0]
    hr_av = int(sum(int(h) for h in hr)/len(hr))
    hr.insert(0, hr_av) 

    return WorkoutDataReturn(time=time, meter=meter, split=split, sr=sr, hr=hr)

   


# def process_variable_intervals(cell_blocks:List[dict], time_row_index:int):
#     # keep first three rows then every other row becomes rest...I think
#     first_rest_row = time_row_index + 3 
#     cell_blocks_restless = cell_blocks[:first_rest_row] + cell_blocks[first_rest_row::2]
#     pass

