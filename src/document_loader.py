import io
import os
from pathlib import Path

from docx import Document as DocxDocument
from PIL import Image
from pptx import Presentation as PptxPresentation
from PyPDF2 import PdfReader


class ExtractedImage:
    """Container for extracted image data with metadata."""
    def __init__(self, image: Image.Image, source: str, page_or_shape: int | str = None):
        self.image = image
        self.source = source  # e.g., "pdf", "docx", "pptx"
        self.page_or_shape = page_or_shape  # page number or shape index
        self.width = image.width
        self.height = image.height
    
    def get_description(self) -> str:
        """Get a brief description of the image."""
        return f"[Image from {self.source}: {self.width}x{self.height}px{f' (page {self.page_or_shape})' if self.page_or_shape else ''}]"


def describe_image(image: Image.Image) -> str:
    """Extract OCR text from image (fallback for text-only mode)."""
    try:
        from pytesseract import image_to_string
        text = image_to_string(image).strip()
        return f"OCR text: {text}" if text else "Image with no readable text"
    except ImportError:
        return "Image (OCR not available)"


def load_text_file(path: Path) -> tuple[str, list[str]]:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return f.read(), []


def load_pdf(path: Path) -> tuple[str, list[ExtractedImage]]:
    text_parts = []
    extracted_images = []
    reader = PdfReader(str(path))
    
    for page_num, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if page_text:
            text_parts.append(page_text)
        
        # Extract images from PDF
        if "/XObject" in page["/Resources"]:
            xobj = page["/Resources"]["/XObject"].get_object()
            for obj_name in xobj:
                obj = xobj[obj_name].get_object()
                if obj["/Subtype"] == "/Image":
                    try:
                        data = obj.get_data()
                        image = Image.open(io.BytesIO(data))
                        if image.size[0] > 50 and image.size[1] > 50:  # Filter out tiny images
                            extracted_images.append(ExtractedImage(image, "pdf", page_num + 1))
                    except Exception as e:
                        pass  # Skip images that can't be decoded
    
    return "\n\n".join(text_parts), extracted_images


def load_docx(path: Path) -> tuple[str, list[ExtractedImage]]:
    doc = DocxDocument(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    extracted_images = []
    
    for inline_shape in doc.inline_shapes:
        try:
            r_id = inline_shape._inline.graphic.graphicData.pic.blipFill.blip.embed
            part = doc.part.related_parts[r_id]
            img_data = part.blob
            image = Image.open(io.BytesIO(img_data))
            if image.size[0] > 50 and image.size[1] > 50:  # Filter out tiny images
                extracted_images.append(ExtractedImage(image, "docx"))
        except Exception:
            pass
    
    for table in doc.tables:
        for row in table.rows:
            row_text = " \t ".join(cell.text for cell in row.cells if cell.text.strip())
            if row_text:
                paragraphs.append(row_text)
    
    return "\n\n".join(paragraphs), extracted_images


def load_pptx(path: Path) -> tuple[str, list[ExtractedImage]]:
    prs = PptxPresentation(str(path))
    text_parts = []
    extracted_images = []
    
    for slide_num, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text_parts.append(shape.text)
            if hasattr(shape, "image"):
                try:
                    img_data = shape.image.blob
                    image = Image.open(io.BytesIO(img_data))
                    if image.size[0] > 50 and image.size[1] > 50:  # Filter out tiny images
                        extracted_images.append(ExtractedImage(image, "pptx", slide_num + 1))
                except Exception:
                    pass
        
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            notes = slide.notes_slide.notes_text_frame.text
            if notes:
                text_parts.append(notes)
    
    return "\n\n".join([part for part in text_parts if part.strip()]), extracted_images


def load_image(path: Path) -> tuple[str, list[ExtractedImage]]:
    try:
        image = Image.open(str(path))
        if image.size[0] > 50 and image.size[1] > 50:  # Only include if reasonably sized
            return f"[Image file: {path.name}]", [ExtractedImage(image, "image", path.name)]
        else:
            return f"[Image file: {path.name} - too small]", []
    except Exception:
        return f"[Image file: {path.name} - could not load]", []


def load_document(path: str) -> tuple[str, list[ExtractedImage]]:
    path_obj = Path(path)
    if path_obj.is_dir():
        documents = []
        extracted_images = []
        for child in sorted(path_obj.iterdir()):
            if child.is_file():
                doc_text, imgs = load_document(str(child))
                documents.append(doc_text)
                extracted_images.extend(imgs)
        return "\n\n".join(documents), extracted_images

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
