from typing import List
import pandas as pd
import boto3
import pdb

client = boto3.client("textract")


def hit_textract_api(erg_image_bytearray):
    return client.analyze_document(
        Document={"Bytes": erg_image_bytearray}, FeatureTypes=["TABLES"]
    )


# Extract Workout Data - Create List[dict] with table data: row, column, text, text_id
def extract_table_data(full_response: dict) -> List[dict]:
    blocks = full_response["Blocks"]
    # create dict {word_id : word_text}
    word_ids = {}
    table_data = []
    for block in blocks:
        if block["BlockType"] == "WORD":
            word_ids[block["Id"]] = block["Text"]
        # create table_data
        elif block["BlockType"] == "CELL":
            # only look at cells with content - eg some cells have no content like Heart Rate column when not HR data was collected
            if "Relationships" in block.keys():
                cell_data = {"row": None, "col": None, "text": None}
                cell_data["row"] = block["RowIndex"]
                cell_data["col"] = block["ColumnIndex"]
                cell_data["text_id"] = block["Relationships"][0]["Ids"][0]
                cell_data["text"] = word_ids[block["Relationships"][0]["Ids"][0]]
                table_data.append(cell_data)
                # Fix for when stroke rate gets lumped in with split
                if (
                    block["ColumnIndex"] == 3
                    and len(block["Relationships"][0]["Ids"]) > 1
                ):
                    table_data.append(
                        {
                            "row": block["RowIndex"],
                            "col": 4,
                            "text": word_ids[block["Relationships"][0]["Ids"][1]],
                            "text_id": block["Relationships"][0]["Ids"][1],
                        }
                    )
    print(table_data)
    return table_data


# clean workout data - replace column labels & change "," for "."
def clean_table_data(table_data: List[dict]):
    table_data[0]["text"] = "time"
    table_data[1]["text"] = "meter"
    table_data[2]["text"] = "split"
    table_data[3]["text"] = "sr"
    for cell in table_data:
        if "," in cell["text"]:
            cell["text"] = cell["text"].replace(",", ".")
    return table_data


# view workout data - visual only
def compile_workout_data(wo_clean: List[dict]) -> dict:
    wo_dict = {"time": [], "meter": [], "split": [], "sr": []}
    for cell in wo_clean:
        if cell["row"] != 1:
            # if cell['row'] == 2:
            #     wo_dict['summary'].append(cell['text'])
            # else:
            if cell["col"] == 1:
                wo_dict["time"].append(cell["text"])
            elif cell["col"] == 2:
                wo_dict["meter"].append(cell["text"])
            elif cell["col"] == 3:
                wo_dict["split"].append(cell["text"])
            elif cell["col"] == 4:
                wo_dict["sr"].append(cell["text"])
    return wo_dict


# extract raw metadata
def extract_metadata(full_response: dict, table_data: List[dict]) -> list:
    raw_meta = []
    first_cell_id = table_data[0]["text_id"]
    for block in full_response["Blocks"]:
        if block["BlockType"] == "PAGE":
            continue
        elif block["BlockType"] == "LINE":
            if first_cell_id in block["Relationships"][0]["Ids"]:  # beginning of table
                break
            else:
                raw_meta.append(block["Text"])
    return raw_meta


# clean metadata
def clean_metadata(raw_meta: list) -> dict:
    # Delete everything before wo_name
    meta = raw_meta
    try:
        view_idx = [
            i for i, item in enumerate(raw_meta) if "View" in item or "Detail" in item
        ][0]
        meta = raw_meta[view_idx + 1 :]
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
    table_data = extract_table_data(raw_response)
    print("table_data: ", table_data)
    table_data_clean = clean_table_data(table_data)
    print("table_data_clean: ", table_data_clean)
    workout_data = compile_workout_data(table_data_clean)
    print("workout_data: ", workout_data)
    workout_df = pd.DataFrame(workout_data)
    print(workout_df)

    raw_meta = extract_metadata(raw_response, table_data)
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
