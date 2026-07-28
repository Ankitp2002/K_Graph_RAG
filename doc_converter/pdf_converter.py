# ==========================================
# 3. CORE PARSING & ENRICHMENT PIPELINE
# ==========================================
from data_ingestion.parser_documents.parser import get_mark_down
from utils import handle_err
from pathlib import Path
from llama_index.core import Document
import os
import pypdfium2
from constant import UNSTRUCTURED_UNSTRUCTURED_DOCUMENT_CONVERT_CHUNK_SIZE


@handle_err
def pdf_parse_and_enrich_document(file_path: str) -> str:
    abs_path = os.path.abspath(file_path)

    # 1. Inspect the file to count total pages with near-zero RAM usage
    pdf = pypdfium2.PdfDocument(abs_path)
    total_pages = len(pdf)
    del pdf  # Drop reference immediately

    print(f"📄 Processing total of {total_pages} pages in chunked blocks...")

    all_markdown_segments = []
    fig_counter = 0
    table_counter = 0

    # 2. Sequential Step-by-Step Chunk Processing
    for start_page in range(
        1, total_pages + 1, UNSTRUCTURED_UNSTRUCTURED_DOCUMENT_CONVERT_CHUNK_SIZE
    ):
        end_page = min(
            start_page + UNSTRUCTURED_UNSTRUCTURED_DOCUMENT_CONVERT_CHUNK_SIZE - 1,
            total_pages,
        )
        print(f"⏳ Parsing chunk window: Pages {start_page} to {end_page}...")

        # 4. Export current mutated chunk to Markdown and add to our list
        chunk_markdown, fig_counter, table_counter = get_mark_down(
            abs_path, start_page, end_page, table_counter, fig_counter
        )
        all_markdown_segments.append(chunk_markdown)

    # 6. Combine all processed slices into a single unified output text
    final_full_markdown = "\n\n".join(all_markdown_segments)

    return final_full_markdown
