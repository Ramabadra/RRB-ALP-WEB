"""
PDF text extractor — two-stage extraction pipeline.

Stage 1: PyMuPDF (fitz) — fast native text extraction.
  Works perfectly for digitally-created PDFs (Born-Digital).
  Returns empty or very short text for scanned PDFs.

Stage 2: OCR fallback via pytesseract + pdf2image.
  Triggered automatically when PyMuPDF extracts less than
  MIN_CHARS_PER_PAGE characters per page on average.
  Converts each page to an image, then runs Tesseract OCR.

The extractor ONLY handles text extraction.
Parsing (splitting text into Q&A structures) is handled by QuestionParser.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

# If PyMuPDF extracts fewer than this many chars/page on average,
# we assume it's a scanned PDF and fall back to OCR.
MIN_CHARS_PER_PAGE = 100


@dataclass
class PageText:
    """Text content of a single PDF page."""
    page_number: int  # 1-indexed
    text: str
    used_ocr: bool = False


@dataclass
class ExtractionResult:
    """Full result of PDF text extraction."""
    pages: List[PageText]
    page_count: int
    used_ocr: bool  # True if OCR was used for any page

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)


class PDFExtractor:
    """
    Two-stage PDF text extractor.

    Usage:
        extractor = PDFExtractor()
        result = extractor.extract(pdf_bytes)
        print(result.page_count, result.used_ocr)
        for page in result.pages:
            print(page.page_number, page.text[:200])
    """

    def extract(self, pdf_bytes: bytes) -> ExtractionResult:
        """
        Extract text from PDF bytes.

        Automatically chooses between native extraction and OCR.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError(
                "PyMuPDF is required for PDF text extraction. "
                "Install with: pip install pymupdf"
            )

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = doc.page_count
        pages: List[PageText] = []

        # ── Stage 1: Native text extraction ───────────────────────────────────
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            pages.append(PageText(page_number=i, text=text, used_ocr=False))

        doc.close()

        # ── Evaluate extraction quality ───────────────────────────────────────
        total_chars = sum(len(p.text) for p in pages)
        avg_chars = total_chars / page_count if page_count > 0 else 0

        if avg_chars >= MIN_CHARS_PER_PAGE:
            logger.info(
                "Native extraction succeeded: %d pages, %.0f avg chars/page",
                page_count, avg_chars,
            )
            return ExtractionResult(pages=pages, page_count=page_count, used_ocr=False)

        # ── Stage 2: OCR fallback ────────────────────────────────────────────
        logger.info(
            "Low text yield (%.0f chars/page avg). Falling back to OCR.",
            avg_chars,
        )
        return self._ocr_extract(pdf_bytes, page_count)

    def _ocr_extract(self, pdf_bytes: bytes, page_count: int) -> ExtractionResult:
        """OCR fallback using pdf2image + pytesseract."""
        try:
            import pdf2image
            import pytesseract
            from PIL import Image
        except ImportError:
            raise ImportError(
                "OCR dependencies missing. Install with: "
                "pip install pdf2image pytesseract Pillow"
            )

        logger.info("Running OCR on %d pages...", page_count)
        pages: List[PageText] = []

        # Convert PDF to images (300 DPI for good OCR quality)
        images = pdf2image.convert_from_bytes(pdf_bytes, dpi=300)

        for i, image in enumerate(images, start=1):
            # English + Hindi OCR (RRB ALP papers can be bilingual)
            text = pytesseract.image_to_string(image, lang="eng+hin")
            pages.append(PageText(page_number=i, text=text.strip(), used_ocr=True))
            logger.debug("OCR page %d: %d chars extracted", i, len(text))

        logger.info("OCR complete: %d pages processed", page_count)
        return ExtractionResult(pages=pages, page_count=page_count, used_ocr=True)
