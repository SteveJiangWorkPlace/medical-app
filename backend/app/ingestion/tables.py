from pathlib import Path

import pandas as pd


def extract_table_preview(path: str, max_rows: int | None = None) -> str:
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        frame = pd.read_csv(file_path, nrows=max_rows)
        return dataframe_to_text(frame)

    if suffix in {".xls", ".xlsx"}:
        sheets = pd.read_excel(file_path, sheet_name=None, nrows=max_rows)
        parts = []
        for sheet_name, frame in sheets.items():
            parts.append(f"[Sheet: {sheet_name}]\n{dataframe_to_text(frame)}")
        return "\n\n".join(parts)

    raise ValueError(f"Unsupported table file type: {suffix}")


def dataframe_to_text(frame: pd.DataFrame) -> str:
    frame = frame.fillna("")
    return frame.to_csv(index=False)
