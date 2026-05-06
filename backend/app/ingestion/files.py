from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


def save_upload_file(upload_dir: str, file: UploadFile) -> tuple[str, str]:
    target_dir = Path(upload_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    original_name = file.filename or "uploaded-file"
    suffix = Path(original_name).suffix
    stored_name = f"{uuid4().hex}{suffix}"
    target_path = target_dir / stored_name

    with target_path.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            output.write(chunk)

    return original_name, str(target_path)
