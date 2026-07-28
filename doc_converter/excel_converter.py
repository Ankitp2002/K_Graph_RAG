import pickle

import pandas as pd
from utils import handle_err


@handle_err
def excel_parse_and_enrich_document(file_path: str, file_name) -> list:
    df = pd.read_excel(
        file_path, sheet_name=None
    )  # Read all sheets into a dictionary of DataFrames

    meta_info = []
    for sheet_name, sheet_df in df.items():
        meta_info.append(
            {"sheet_name": sheet_name, "header": sheet_df.columns.tolist()}
        )

    with open(file_name, "wb") as f:
        pickle.dump(df, f)

    return meta_info
