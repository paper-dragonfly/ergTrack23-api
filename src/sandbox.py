import json
import pdb

d = {"dan": {"name": "daniel", "age": 22}, "sam": {"name": "samuel", "age": 33}}


def write_to_rawocr(content):
    with open("src/rawocr.json", "w") as f:
        json.dump(content, f)


pdb.set_trace()
write_to_rawocr(d)

image_sent = True
# is file name in library already
if image_sent:
    with open("src/rawocr.json", "r") as f:
        rawocr = json.load(f)
    if "kaja" in rawocr.keys():
        raw_data = rawocr["kaja"]
        print("kaja in library", raw_data)
    else:
        print("kaja not in library")
        # create bytearrray -> textract ->add to dict ->write over
        resp = {"name": "kathleen", "age": 22}
        rawocr["kaja"] = resp
        with open("src/rawocr.json", "w") as f:
            json.dump(rawocr, f)


# if yes, load file
# if no, hit textract API and save results
