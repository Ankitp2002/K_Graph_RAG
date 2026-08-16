import gc
from docling_core.types.doc.document import (
    TableItem,
    PictureItem,
    TextItem,
    DocItemLabel,
)
from pathlib import Path
from constant import IMAGE_OUTPUT_DIR
from utils import handle_err
import os
import pypdfium2
from constant import UNSTRUCTURED_UNSTRUCTURED_DOCUMENT_CONVERT_CHUNK_SIZE
import zipfile
from docx import Document as docx_doc
from lxml import etree
import pandas as pd
import pickle


class UnstructuredConverter:
    __slot__ = []

    @handle_err
    def pdf_parse_and_enrich_document(self) -> str:
        abs_path = os.path.abspath(self.file_path)

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
            chunk_markdown, fig_counter, table_counter = self._get_mark_down(
                abs_path, start_page, end_page, table_counter, fig_counter
            )
            all_markdown_segments.append(chunk_markdown)

        # 6. Combine all processed slices into a single unified output text
        final_full_markdown = "\n\n".join(all_markdown_segments)

        return final_full_markdown

    @handle_err
    @staticmethod
    def __get_docx_page_count(abs_path: str) -> int:
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

    @handle_err
    def docx_parse_and_enrich_document(self) -> str:
        abs_path = os.path.abspath(self.file_path)

        # 1. Count the pages dynamically using DOCX metadata
        total_pages = self.__get_docx_page_count(abs_path)

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
            chunk_markdown, fig_counter, table_counter = self._get_mark_down(
                abs_path, start_page, end_page, table_counter, fig_counter
            )
            all_markdown_segments.append(chunk_markdown)

        # 6. Combine all processed slices into a single unified output text
        final_full_markdown = "\n\n".join(all_markdown_segments)

        return final_full_markdown


class StructuredConverter:
    __slot__ = []

    def __init__(self, file_path, file_name):
        self.file_path = file_path
        self.file_name = file_name

    @handle_err
    def csv_parse_and_enrich_document(self) -> list:
        df = pd.read_csv(self.file_path)
        df.to_pickle(self.file_name)
        return [{"sheet_name": "default", "header": df.columns.tolist()}]

    @handle_err
    def excel_parse_and_enrich_document(self) -> list:
        df = pd.read_excel(self.file_path, sheet_name=None)

        meta_info = []
        for sheet_name, sheet_df in df.items():
            meta_info.append(
                {"sheet_name": sheet_name, "header": sheet_df.columns.tolist()}
            )

        with open(self.file_name, "wb") as f:
            pickle.dump(df, f)

        return meta_info


class BaseConverter(UnstructuredConverter, StructuredConverter):
    __slot__ = []

    def __init__(self, file_path, extention, llm_instance, docling_converter):
        self.file_path = file_path
        self.extention = extention
        self.llm_instance = llm_instance
        self.docling_converter = docling_converter

    @handle_err
    def __replace_image_table_with_summary(
        self, doc, element, table_counter, fig_counter, abs_path
    ) -> tuple[int, ...]:
        # Maintain correct index across chunks
        if isinstance(element, TableItem):
            element_type = "table"
            fig_index = table_counter
            table_counter += 1
        else:
            element_type = "fig"
            fig_index = fig_counter
            fig_counter += 1

        # Save visual crop element
        img_format = element.image.pil_image.format or "PNG"
        image_filename = (
            f"{Path(abs_path).stem}_{element_type}_{fig_index}.{img_format.lower()}"
        )
        image_path = IMAGE_OUTPUT_DIR / image_filename

        with open(image_path, "wb") as f:
            element.image.pil_image.save(f, format=img_format)

        print(
            f"🖼️ Intercepting tag: Processing {element_type}_{fig_index} with Grok..."
        )
        summary = self.llm_instance.get_grok_image_summary(image_path)

        page_no = "Unknown"
        if hasattr(element, "prov") and element.prov:
            page_no = getattr(element.prov[0], "page_no", "Unknown")

        # Build replacement string block
        rich_markdown_replacement = (
            f"\n\n"
            f"### [Visual Data Asset: {element_type.upper()} {fig_index}]\n"
            f"Local Source Reference Path: `{image_path.as_posix()}`\n"
            f"Document Page Location: Page {page_no}\n"
            f"Image Visual Content Analysis: {summary}\n"
            f"### [End of Visual Data Asset]\n"
            f"\n\n"
        )

        new_text_item = TextItem(
            self_ref=element.self_ref,
            parent=element.parent,
            label=DocItemLabel.TEXT,
            text=rich_markdown_replacement,
            orig=rich_markdown_replacement,
        )

        # Mutate tree segment
        doc.replace_item(old_item=element, new_item=new_text_item)

        # Close image stream immediately to drop RAM footprint
        element.image.pil_image.close()
        return fig_counter, table_counter

    @handle_err
    def _get_mark_down(
        self,
        abs_path: str,
        start_page: int,
        end_page: int,
        table_counter: int,
        fig_counter: int,
    ) -> tuple[str, int, int]:
        # Pull only this tiny section into RAM
        result = self.docling_converter.converter.convert(
            abs_path, raises_on_error=False, page_range=(start_page, end_page)
        )

        doc = result.document

        if not result or not result.document:
            return doc.export_to_markdown()

        # 3. Snapshot loop for safe item mutation within the chunk
        for element, _level in list(doc.iterate_items()):
            if isinstance(element, (PictureItem, TableItem)):
                if (
                    hasattr(element, "image")
                    and element.image
                    and hasattr(element.image, "pil_image")
                ):
                    fig_counter, table_counter = (
                        self.__replace_image_table_with_summary(
                            doc, element, table_counter, fig_counter, abs_path
                        )
                    )

        markdown = doc.export_to_markdown()

        del result
        del doc
        gc.collect()

        return markdown, fig_counter, table_counter

    @handle_err
    def parse_and_enrich_document(self) -> tuple[str, list]:
        if self.extention == ".pdf":
            markdown = self.pdf_parse_and_enrich_document()
            return markdown, []
        elif self.extention == ".docx":
            markdown = self.docx_parse_and_enrich_document()
            return markdown, []
        elif self.extention == ".csv":
            meta_info = self.csv_parse_and_enrich_document()
            return "", meta_info
        elif self.extention in [".xls", ".xlsx"]:
            meta_info = self.excel_parse_and_enrich_document()
            return "", meta_info
        else:
            raise ValueError(f"Unsupported file extension: {self.extention}")
