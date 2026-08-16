import os
from pathlib import Path

UPLOAD_DIR = "/tmp/user_files_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Define a safe chunk window (e.g., 5 pages at a time to prevent RAM spikes)
UNSTRUCTURED_UNSTRUCTURED_DOCUMENT_CONVERT_CHUNK_SIZE = 5
STRUCTURED_DOCUMENT_CONVERT_CHUNK_SIZE = 50000

IMAGE_OUTPUT_DIR = Path("./extracted_images")
IMAGE_OUTPUT_DIR.mkdir(exist_ok=True)
