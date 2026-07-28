import pandas as pd
from config import TEMP_DIR
from utils import handle_err_and_raise


@handle_err_and_raise
def csv_parse_and_enrich_document(file_path: str, file_name: str) -> list:
    df = pd.read_csv(file_path)
    df.to_pickle(file_name)
    return [{"sheet_name": "default", "header": df.columns.tolist()}]
