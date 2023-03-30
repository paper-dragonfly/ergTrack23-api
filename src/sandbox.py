from src.ocr import process_raw_ocr
from rawocr import RAW3_erg01, Raw4_cr_erg01
import pdb

# pdb.set_trace()
workout_ocr = process_raw_ocr(Raw4_cr_erg01)
print(workout_ocr)
