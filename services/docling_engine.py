# =====================================================================
# STARTUP LAYER: PRELOAD MODELS INTO MEMORY IMMEDIATELY
# =====================================================================
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    WordFormatOption,
    ExcelFormatOption,
    CsvFormatOption,
)
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureOptions,
    PaginatedPipelineOptions,
)
from docling.datamodel.base_models import InputFormat

print("📥 Preloading Docling Engines and RapidOCR Models into RAM...")
# =====================================================================


class DoclingEngine:

    __slot__ = ["converter"]

    def __init__(self):
        self.converter: DocumentConverter | None = None

    def __pdf_config(self):
        # =====================================================================
        # PDF configuration
        # =====================================================================
        # Define structural pipeline parameters globally
        pdf_pipeline_options = PdfPipelineOptions()
        pdf_pipeline_options.do_table_structure = True
        pdf_pipeline_options.do_ocr = True

        # pdf_pipeline_options.do_code_enrichment = True
        # pdf_pipeline_options.do_formula_enrichment = True

        pdf_pipeline_options.images_scale = 2.0
        pdf_pipeline_options.generate_page_images = True
        pdf_pipeline_options.generate_picture_images = True
        pdf_pipeline_options.generate_table_images = True

        pdf_pipeline_options.generate_parsed_pages = True
        pdf_pipeline_options.table_structure_options = TableStructureOptions(
            do_cell_matching=True
        )

        pdf_strict_format_options = PdfFormatOption(
            pipeline_options=pdf_pipeline_options
        )
        return pdf_strict_format_options

    def __docx_config(self):
        # =====================================================================
        # DOCX configuration
        # =====================================================================
        # 1. Configure pipeline options
        docx_pipeline_options = PaginatedPipelineOptions()
        docx_pipeline_options.generate_picture_images = True
        docx_pipeline_options.images_scale = 2.0

        word_strict_format_options = WordFormatOption(
            pipeline_options=docx_pipeline_options
        )
        # =====================================================================
        return word_strict_format_options

    def __xlsx_config(self):
        # =====================================================================
        # EXCEL configuration
        # =====================================================================
        excel_strict_format_options = ExcelFormatOption()
        # =====================================================================
        return excel_strict_format_options

    def __available_formats(self):
        # =====================================================================
        # Configuration all possible pipelines
        # =====================================================================
        format_to_options = {
            InputFormat.PDF: self.__pdf_config(),
            InputFormat.DOCX: self.__docx_config(),
            InputFormat.XLSX: self.__xlsx_config(),
        }

        avl_pipeline = list(format_to_options.keys())
        return avl_pipeline, format_to_options

    def initialize(self):
        avl_pipeline, format_to_options = self.__available_formats()
        # =====================================================================
        # =====================================================================
        # Instantiate the single global converter instance
        # =====================================================================
        self.converter = DocumentConverter(
            allowed_formats=avl_pipeline, format_options=format_to_options
        )
        for pipeline_init in avl_pipeline:
            self.converter.initialize_pipeline(pipeline_init)
        # =====================================================================

    def get_converter(self) -> DocumentConverter:
        if self.converter is None:
            raise ValueError(
                "DoclingEngine is not initialized. Call initialize() first."
            )
        return self.converter

    def close(self):
        if self.converter is not None:
            self.converter.close()
            self.converter = None
