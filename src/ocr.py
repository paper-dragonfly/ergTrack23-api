from typing import List, Dict
import pandas as pd
import boto3
import pdb

client = boto3.client("textract")


def hit_textract_api(erg_image_bytearray):
    return client.analyze_document(
        Document={"Bytes": erg_image_bytearray}, FeatureTypes=["TABLES"]
    )


# Extract Workout Data - Create List[dict] with table data: row, column, text, text_id
def create_word_index(image_raw_response: dict) -> dict:
    # create dict {word_id : word_text}
    word_blocks: List[dict] = [
        block for block in image_raw_response["Blocks"] if block["BlockType"] == "WORD"
    ]
    word_index = {}
    for block in word_blocks:
        word_index[block["Id"]] = block["Text"]
    return word_index


def extract_table_data(image_raw_response: dict, word_index: dict) -> List[dict]:
    # check num_cols then create table_data
    cell_blocks: List[dict] = [
        block for block in image_raw_response["Blocks"] if block["BlockType"] == "CELL"
    ]
    num_cols = cell_blocks[-1]["ColumnIndex"]
    print(f"num cols: {num_cols}")
    if not 3 < num_cols < 6:
        return (False, "invalid column count")
    table_data = []
    for block in cell_blocks:
        #  if cell is empty, add empty entry. Ignore HR column.
        if not "Relationships" in block.keys() and block["ColumnIndex"] < 5:
            # if previous block didn't corect empty cell, add empty entry - see FIX  below
            if not (
                table_data[-1]["row"] == block["RowIndex"]
                and table_data[-1]["col"] == block["ColumnIndex"]
            ):
                cell_data = {
                    "row": block["RowIndex"],
                    "col": block["ColumnIndex"],
                    "text": [""],
                }
                table_data.append(cell_data)
        # deal with cells in columns 1-4 that have content
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
    # print(table_data)
    return table_data


# clean workout data - replace column labels & change "," for "."
def clean_table_data(table_data: List[dict]):
    # remove all cells before 'time'
    while "time" not in table_data[0]["text"]:
        del table_data[0]
    table_data[0]["text"] = ["time"]
    table_data[1]["text"] = ["meter"]
    table_data[2]["text"] = ["split"]
    table_data[3]["text"] = ["sr"]
    for cell in table_data:
        for word in cell["text"]:
            if "," in word:
                word_index = cell["text"].index(word)
                cell["text"][word_index] = word.replace(",", ".")
    return table_data


# view workout data - visual only
def compile_workout_data(wo_clean: List[dict]) -> Dict[str, List[str]]:
    col_head_row = wo_clean[0]["row"]
    wo_dict = {"time": [], "meter": [], "split": [], "sr": []}
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
    return wo_dict


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
    for block in line_blocks:
        if time_id in block["Relationships"][0]["Ids"]:
            break
        else:
            raw_meta.append(block["Text"])
    return raw_meta


# clean metadata
def clean_metadata(raw_meta: list) -> dict:
    # Delete everything before wo_name
    meta = raw_meta
    try:
        view_detail_idx = [
            i for i, item in enumerate(raw_meta) if "View" in item or "Detail" in item
        ][0]
        meta = raw_meta[view_detail_idx + 1 :]
    except:
        pass
    for i in range(len(meta)):
        try:
            meta[i] = meta[i].replace(",", ".")
        except:
            pass
    if len(meta) == 2:
        meta_dict = {"wo_name": meta[0], "date": meta[1]}
    elif len(meta) >= 4:
        meta_dict = {
            "workout_name": meta[0],
            "total_type": meta[1],
            "workout_date": meta[2],
            "total_val": meta[3],
        }
    return meta_dict


def process_raw_ocr(raw_response: dict):
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

    return {"workout_meta": clean_meta, "workout_data": workout_data}
