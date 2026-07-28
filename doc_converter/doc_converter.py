# ==========================================
# 3. CORE PARSING & ENRICHMENT PIPELINE
# ==========================================
from data_ingestion.parser_documents.parser import get_mark_down
from utils import handle_err_and_raise
from pathlib import Path
from llama_index.core import Document
import os
from constant import UNSTRUCTURED_UNSTRUCTURED_DOCUMENT_CONVERT_CHUNK_SIZE
import os
import zipfile
from docx import Document as docx_doc
from lxml import etree


def get_docx_page_count(abs_path: str) -> int:
    """
    Extracts the estimated/declared total pages from the Word document's
    core metadata properties (app.xml) without fully rendering the document.
    Fallback is 1 if the property isn't found.
    """
    try:
        with zipfile.ZipFile(abs_path) as zf:
            if "docProps/app.xml" in zf.namelist():
                xml_content = zf.read("docProps/app.xml")
                root = etree.fromstring(xml_content)
                # Find the <Pages> tag in the app.xml
                pages_elem = root.find("{http://openxmlformats.org}Pages")
                if pages_elem is not None and pages_elem.text:
                    return int(pages_elem.text)
    except Exception as e:
        print(f"⚠️ Could not read docProps/app.xml: {e}")

    # Fallback to counting paragraphs if metadata is unavailable
    try:
        doc = docx_doc(abs_path)
        page_count = sum(p.contains_page_break for p in doc.paragraphs) + 1
        return page_count
    except Exception:
        return 1


@handle_err_and_raise
def docx_parse_and_enrich_document(file_path: str) -> str:
    abs_path = os.path.abspath(file_path)

    # 1. Count the pages dynamically using DOCX metadata
    total_pages = get_docx_page_count(abs_path)

    print(f"Processing total of {total_pages} estimated pages in chunked blocks...")

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
