import io
import os
from pathlib import Path

from docx import Document as DocxDocument
from PIL import Image
from pptx import Presentation as PptxPresentation
from PyPDF2 import PdfReader


def describe_image(image: Image.Image) -> str:
    try:
        from pytesseract import image_to_string
        text = image_to_string(image).strip()
        return f"OCR text: {text}" if text else "Image with no readable text"
    except ImportError:
        return "Image (OCR not available)"


def load_text_file(path: Path) -> tuple[str, list[str]]:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return f.read(), []


def load_pdf(path: Path) -> tuple[str, list[str]]:
    text_parts = []
    reader = PdfReader(str(path))
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text:
            text_parts.append(page_text)
    # TODO: Extract embedded images from PDF (requires additional library like pdfplumber)
    return "\n\n".join(text_parts), []


def load_docx(path: Path) -> tuple[str, list[str]]:
    doc = DocxDocument(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    image_descriptions = []
    for inline_shape in doc.inline_shapes:
        try:
            r_id = inline_shape._inline.graphic.graphicData.pic.blipFill.blip.embed
            part = doc.part.related_parts[r_id]
            img_data = part.blob
            image = Image.open(io.BytesIO(img_data))
            desc = describe_image(image)
            image_descriptions.append(desc)
        except Exception:
            pass
    for table in doc.tables:
        for row in table.rows:
            row_text = " \t ".join(cell.text for cell in row.cells if cell.text.strip())
            if row_text:
                paragraphs.append(row_text)
    return "\n\n".join(paragraphs), image_descriptions


def load_pptx(path: Path) -> tuple[str, list[str]]:
    prs = PptxPresentation(str(path))
    text_parts = []
    image_descriptions = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text_parts.append(shape.text)
            if hasattr(shape, "image"):
                try:
                    img_data = shape.image.blob
                    image = Image.open(io.BytesIO(img_data))
                    desc = describe_image(image)
                    image_descriptions.append(desc)
                except Exception:
                    pass
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            notes = slide.notes_slide.notes_text_frame.text
            if notes:
                text_parts.append(notes)
    return "\n\n".join([part for part in text_parts if part.strip()]), image_descriptions


def load_image(path: Path) -> tuple[str, list[str]]:
    try:
        from pytesseract import image_to_string
    except ImportError:
        image_to_string = None

    if image_to_string is None:
        return f"[Image file: {path.name} - install pytesseract for OCR text extraction]", []

    image = Image.open(str(path))
    extracted = image_to_string(image)
    text = extracted or f"[Image file: {path.name} - no text found via OCR]"
    return text, []


def load_document(path: str) -> tuple[str, list[str]]:
    path_obj = Path(path)
    if path_obj.is_dir():
        documents = []
        image_descriptions = []
        for child in sorted(path_obj.iterdir()):
            if child.is_file():
                doc_text, img_descs = load_document(str(child))
                documents.append(doc_text)
                image_descriptions.extend(img_descs)
        return "\n\n".join(documents), image_descriptions

    ext = path_obj.suffix.lower()
    if ext in {".txt", ".md", ".csv", ".json"}:
        return load_text_file(path_obj)
    if ext == ".pdf":
        return load_pdf(path_obj)
    if ext == ".docx":
        return load_docx(path_obj)
    if ext == ".pptx":
        return load_pptx(path_obj)
    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}:
        return load_image(path_obj)

    raise ValueError(f"Unsupported input file type: {ext}")
