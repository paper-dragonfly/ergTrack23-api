from typing import List, Dict, Union
import pandas as pd
import boto3
import pdb
import yaml
from src.schemas import OcrDataReturn, CleanMetaReturn, WorkoutDataReturn
from src.schemas import CustomError, CellData

# Load config file values
with open("config/config.yaml", "r") as f:
    config_data = yaml.load(f, Loader=yaml.FullLoader)

ACCESS_KEY = config_data["AWS_ACCESS_KEY_ID"]
SECRET_KEY = config_data["AWS_SECRET_ACCESS_KEY"]

client = boto3.client("textract", aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,region_name="us-east-1")


def hit_textract_api(erg_image_bytearray):
    try:
        return client.analyze_document(
            Document={"Bytes": erg_image_bytearray}, FeatureTypes=["TABLES"]
        )
    except Exception as e:
        raise CustomError(f"hit_textract_api failed, {e}")


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
        raise CustomError(f"create_word_index failed, {e}")


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
            print("remove", block["RowIndex"], block["ColumnIndex"])
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
        #for rows with data (i.e. not column headings) 
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
    for r in range(1,num_rows):  # fm 1 because first row is blank
        for c in range(1,6): #cols 1-5
            #add empty HR cell - no HR data
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
    print(table_data)
    return table_data


def add_empty_cell_if_needed(table_data, block) -> Union[dict, bool]:
    # if previous block didn't correct empty cell, add empty entry - see FIX  below
    # fix (i.e. not needed) would apply if SR had been lumped in with split or HR lumped in with SR
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
        print('blocks before time removed')
        print('cell blocks len', len(cell_blocks))
        
        # CHECK number of columns
        num_cols = cell_blocks[-1]["ColumnIndex"]
        print(f"num cols: {num_cols}")

        if not 1 < num_cols < 7:
            raise CustomError("extract_table_data failed, invalid column count")
        #if num cols is 6 check if last two cols are empty and delete them if they are
        if num_cols == 6:
            #create list of all col 5 and 6 cells
            col56 = [block for block in cell_blocks if block['ColumnIndex'] in [5,6]]
            content = False
            # check if empty
            for block in col56:
                if "Relationships" in block.keys():
                    content = True 
            if not content:
                cell_blocks  = [block for block in cell_blocks if block['ColumnIndex'] not in [5,6]] 
                num_cols = 4              
            
        # if num cols is 2 or three seperate merged cols:
        if num_cols < 4:
            print("Merged cols detected")
            table_data = process_merged_cols(cell_blocks, time_row_index, word_index) # TODO: come back to add HR
        else: 
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
                    # FIX for when stroke rate gets lumped in with split but still recognized as two words
                    if block["ColumnIndex"] == 3 and len(cell_data["text_ids"]) > 1:
                        table_data.append(
                            {
                                "row": block["RowIndex"],
                                "col": 4,
                                "text": [word_index[cell_data["text_ids"][-1]]],
                                "text_id": [cell_data["text_ids"][-1]],
                            }
                        )
                    #FIX HR gets lumped in with SR in col4 either as two words or as one 
                    if block["ColumnIndex"] == 4 and (len(cell_data["text_ids"]) > 1 or 4 < len(cell_data['text'][0]) < 7):
                        #delete most recent cell entry in table_data - it contains the merged SR/HR data
                        del table_data[-1] 
                        # isolate SR and HR data 
                        if len(cell_data["text_ids"]) > 1:
                            sr = cell_data['text'][0]
                            hr = cell_data['text'][1] 
                            sr_text_id = cell_data['text_ids'][0]
                            hr_text_id = ['from SR'] #for debugging
                        else: 
                            sr = cell_data['text'][0][:2]
                            hr = cell_data["text"][0][2:].strip()
                            sr_text_id = ['altered - SRHR split'] #for debugging
                            hr_text_id = ['from SR'] #for debugging
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
                        if table_data[4]['row'] == 2:
                            hr_head = {
                                "row": table_data[0]['row'],
                                "col": 5,
                                "text": ['hr'],
                                "text_id": ['fm manual']
                            }
                        
                            table_data.insert(4,hr_head)                        
                    # FIX SR gets lumped in with HR in col5 either as two words or as one (* assumes len(sr)==2, len(hr)==3)
                    if block["ColumnIndex"] == 5 and (len(cell_data["text_ids"]) > 1 or 4 < len(cell_data['text'][0]) < 7):
                        # cell most recently added to table_data will be missing text - populate it from this HR cell
                        if len(cell_data["text_ids"]) > 1:
                            table_data[-2]["text"][0] = cell_data['text'][0]
                            table_data[-2]["text_ids"] = ['from HR'] #not neccessary but helpful for debugging 
                            del table_data[-1]["text"][0]
                            del table_data[-1]["text_ids"][0] #not neccessary but cleaner
                        else: 
                            sr = cell_data['text'][0][:2]
                            hr = cell_data["text"][0][2:].strip()
                            table_data[-2]["text"][0] = sr
                            table_data[-2]["text_ids"] = ['from HR'] #not neccessary - helpful for debugging
                            table_data[-1]["text"][0] = hr
                            table_data[-1]["text_ids"] = ['altered - SRHR split'] #not neccessary - helpful for debugging
            # Add HR col - all empty
            if num_cols == 4 and table_data[-1]['col'] == 4:
                for i in range(len(table_data) // 4):
                    hr_index = (i + 1) * 5 -1
                    first_data_row = table_data[0]['row']
                    cell_data = {
                        "row": first_data_row + i,
                        "col": 5,
                        "text": [""],
                    }
                    table_data.insert(hr_index, cell_data)
        return table_data
    except Exception as e:
        raise CustomError(f"extract_table_data failed, {e}")


# clean workout data - replace column labels & change "," for "."
def clean_table_data(table_data: List[dict]):
    try:
        # remove all cells before 'time'
        while "time" not in table_data[0]["text"]:
            del table_data[0]
        #add col headings
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
        raise CustomError(f"clean_table_data failed, {e}")


# view workout data - visual only
def compile_workout_data(wo_clean: List[dict]) -> WorkoutDataReturn:
    try:
        col_head_row = wo_clean[0]["row"]
        wo_dict = {"time": [], "meter": [], "split": [], "sr": [], "hr": []}
        for cell in wo_clean:
            if cell["row"] > col_head_row:
                if cell["col"] == 1:
                    wo_dict["time"].append(cell["text"][0])
                elif cell["col"] == 2:
                    wo_dict["meter"].append(cell["text"][0])
                elif cell["col"] == 3:
                    wo_dict["split"].append(cell["text"][0])
                elif cell["col"] == 4:
                    wo_dict["sr"].append(cell["text"][0])
                elif cell["col"] == 5:
                    wo_dict["hr"].append(cell["text"][0])
        if wo_dict['meter'][-1] and not wo_dict['time'][-1]:
            for lst in  wo_dict.values():
                del lst[-1]          
        return wo_dict
    except Exception as e:
        raise CustomError("compile_workout_data failed, invalid column count")


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
def clean_metadata(raw_meta: list) -> CleanMetaReturn:
    # Delete everything before wo_name
    meta = raw_meta
    try:
        view_detail_idx = [
            i for i, item in enumerate(raw_meta) if "View" in item or "Detail" in item or "Verification:" in item
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
    if 2<= len(meta) <= 3:
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


def process_raw_ocr(raw_response: dict, photo_hash: str) -> OcrDataReturn:
    # pdb.set_trace()
    word_index = create_word_index(raw_response)
    table_data = extract_table_data(raw_response, word_index)
    print("table_data: ", table_data)
    table_data_clean = clean_table_data(table_data)
    print("table_data_clean: ", table_data_clean)
    workout_data = compile_workout_data(table_data_clean)
    print("workout_data: ", workout_data)
    workout_df = pd.DataFrame(workout_data)
    print(workout_df)

    raw_meta = extract_metadata(word_index, raw_response)
    print("raw_meta: ", raw_meta)
    clean_meta = clean_metadata(raw_meta)

    # Print Pretty
    print("Metadata")
    for m in clean_meta:
        print(m + ":", clean_meta[m])
    # print(clean_metadata(raw_meta))
    print("\nWorkout Data")
    print(workout_df)

    processed_data = OcrDataReturn(workout_meta=clean_meta, workout_data=workout_data, photo_hash=photo_hash)
    return processed_data
