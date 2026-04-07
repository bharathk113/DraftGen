import argparse
import json
import logging
import os
import sys
from pathlib import Path

from document_loader import load_document, ExtractedImage
from llm_client import LLMClient
from presentation_builder import PresentationBuilder
from report_builder import ReportBuilder

logging.basicConfig(level=logging.INFO, format="%(message)s")

DEFAULT_MAX_SLIDES = 30

SLIDE_PROMPT_TEXT_ONLY = """You are a helpful assistant that creates slide outlines from document content.

Input Document:
{document_text}

User Request:
{user_request}

Generate a JSON object with the key `slides` containing a list of slides. Each slide should include:
- `title` (a slide heading)
- `bullets` (a list of short bullet points; do not put title text here)
- optional `notes`
- optional `images` (list of integer image IDs to include on this slide, if images would enhance the slide)

Ensure `title` is only the slide title and `bullets` are only bullet text.
Do not include any explanation outside the JSON object.
"""

SLIDE_PROMPT_WITH_IMAGES = """You are a helpful assistant that creates slide outlines from document content and images.

Input Document:
{document_text}

Available Images:
{image_descriptions}

User Request:
{user_request}

Analyze the images and decide which ones are relevant to include in the presentation. If the user request mentions images, visuals, or pictures, you MUST include appropriate images.

Generate a JSON object with the key `slides` containing a list of slides. Each slide should include:
- `title` (a slide heading)
- `bullets` (a list of short bullet points that incorporate insights from both text and images)
- optional `notes` (can reference specific findings from the images)
- optional `images` (list of integer image IDs from the available images to include on this slide)

Ensure `title` is only the slide title and `bullets` are only bullet text.
Do not include any explanation outside the JSON object.
"""

REPORT_PROMPT_TEXT_ONLY = """You are a helpful assistant that writes a structured report from document content.

Input Document:
{document_text}

User Request:
{user_request}

Generate a JSON object with the keys `title` and `sections`. Each section should include:
- `heading`
- `content` (a paragraph or list of paragraphs)
- optional `images` (list of integer image IDs to include in this section, if images would enhance the section)

Do not include any explanation outside the JSON object.
"""

REPORT_PROMPT_WITH_IMAGES = """You are a helpful assistant that writes a structured report from document content and visual materials.

Input Document:
{document_text}

Available Images:
{image_descriptions}

User Request:
{user_request}

Analyze the images and decide which ones are relevant to include in the report. If the user request mentions images, visuals, or pictures, you MUST include appropriate images.

Generate a JSON object with the keys `title` and `sections`. Each section should include:
- `heading`
- `content` (a paragraph or list of paragraphs that integrate insights from both text and visual materials)
- optional `images` (list of integer image IDs from the available images to include in this section)

Ensure all findings from the images are properly incorporated into the report content.
Do not include any explanation outside the JSON object.
"""

SLIDE_PROMPT_IMAGE_ONLY = """You are a helpful assistant that creates slide outlines from visual materials.

Available Images:
{image_descriptions}

User Request:
{user_request}

Analyze the images and decide which ones are relevant to include in the presentation. If the user request mentions images, visuals, or pictures, you MUST include appropriate images.

Generate a JSON object with the key `slides` containing a list of slides. Each slide should include:
- `title` (a slide heading based on the visual content)
- `bullets` (a list of short bullet points that summarize insights from the images)
- optional `notes` (can detail specific findings from the images)
- optional `images` (list of integer image IDs from the available images to include on this slide)

Ensure `title` is only the slide title and `bullets` are only bullet text.
Do not include any explanation outside the JSON object.
"""

REPORT_PROMPT_IMAGE_ONLY = """You are a helpful assistant that writes a structured report from visual materials.

Available Images:
{image_descriptions}

User Request:
{user_request}

Analyze the images and decide which ones are relevant to include in the report. If the user request mentions images, visuals, or pictures, you MUST include appropriate images.

Generate a JSON object with the keys `title` and `sections`. Each section should include:
- `heading`
- `content` (a paragraph or list of paragraphs describing findings from the images)
- optional `images` (list of integer image IDs from the available images to include in this section)

Ensure all findings from the visual materials are properly incorporated into the report content.
Do not include any explanation outside the JSON object.
"""


def parse_json_output(raw_text):
    # First, try to extract from ```json code block
    import re
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Fallback: try the whole text
    try:
        return json.loads(raw_text.strip())
    except json.JSONDecodeError:
        pass

    # Fallback: find first { to last }
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw_text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("Unable to parse JSON response from LLM")


def create_image_descriptions(extracted_images):
    descriptions = []
    for i, img in enumerate(extracted_images):
        desc = f"Image {i}: {img.get_description()}"
        descriptions.append(desc)
    return "\n".join(descriptions)


def build_slides_content(document_text, extracted_images, user_request, llm_client, max_slides):
    has_text = document_text.strip() if document_text else False
    has_images = bool(extracted_images)
    
    if not has_text and not has_images:
        raise ValueError("No content (text or images) could be extracted from the document(s)")
    
    image_descriptions = create_image_descriptions(extracted_images) if extracted_images else ""
    
    # Check if user request mentions images
    user_wants_images = any(word in user_request.lower() for word in ["image", "picture", "visual", "chart", "graph", "diagram"])
    
    if extracted_images and llm_client.backend in {"google", "openai"}:
        # Use vision API with images
        images_to_send = [img.image for img in extracted_images]
        
        # Choose appropriate prompt based on content type
        if has_text:
            prompt = SLIDE_PROMPT_WITH_IMAGES.format(
                document_text=document_text,
                image_descriptions=image_descriptions,
                user_request=user_request
            )
        else:
            # Image-only mode
            prompt = SLIDE_PROMPT_IMAGE_ONLY.format(
                image_descriptions=image_descriptions,
                user_request=user_request
            )
        
        logging.info("Using vision API with %d image(s) for slide generation (text: %s)", 
                    len(images_to_send), "yes" if has_text else "no")
        raw = llm_client.generate_with_images(prompt, images_to_send, max_tokens=1000000)
    else:
        # Fallback to text-only mode
        if extracted_images:
            logging.warning("Vision mode not available for current backend; using text-only mode")
        if not has_text:
            raise ValueError("No text content in document and vision API not available. Use --backend openai or --backend google with image-containing documents")
        
        prompt = SLIDE_PROMPT_TEXT_ONLY.format(document_text=document_text, user_request=user_request)
        raw = llm_client.generate(prompt, max_tokens=1000000)
    
    logging.info("LLM raw slide response:\n%s", raw)
    result = parse_json_output(raw)
    slides = result.get("slides", [])
    
    # If user wants images but none suggested, force some images on slides
    if user_wants_images and extracted_images and not any(slide.get("images") for slide in slides):
        logging.info("User requested images but none suggested; adding images to slides")
        for i, slide in enumerate(slides):
            if i < len(extracted_images):
                slide["images"] = [i]
    
    if len(slides) > max_slides:
        logging.info("Truncating slides from %d to %d", len(slides), max_slides)
        slides = slides[:max_slides]
    return slides


def build_report_content(document_text, extracted_images, user_request, llm_client):
    has_text = document_text.strip() if document_text else False
    has_images = bool(extracted_images)
    
    if not has_text and not has_images:
        raise ValueError("No content (text or images) could be extracted from the document(s)")
    
    image_descriptions = create_image_descriptions(extracted_images) if extracted_images else ""
    
    # Check if user request mentions images
    user_wants_images = any(word in user_request.lower() for word in ["image", "picture", "visual", "chart", "graph", "diagram"])
    
    if extracted_images and llm_client.backend in {"google", "openai"}:
        # Use vision API with images
        images_to_send = [img.image for img in extracted_images]
        
        # Choose appropriate prompt based on content type
        if has_text:
            prompt = REPORT_PROMPT_WITH_IMAGES.format(
                document_text=document_text,
                image_descriptions=image_descriptions,
                user_request=user_request
            )
        else:
            # Image-only mode
            prompt = REPORT_PROMPT_IMAGE_ONLY.format(
                image_descriptions=image_descriptions,
                user_request=user_request
            )
        
        logging.info("Using vision API with %d image(s) for report generation (text: %s)", 
                    len(images_to_send), "yes" if has_text else "no")
        raw = llm_client.generate_with_images(prompt, images_to_send, max_tokens=4096)
    else:
        # Fallback to text-only mode
        if extracted_images:
            logging.warning("Vision mode not available for current backend; using text-only mode")
        if not has_text:
            raise ValueError("No text content in document and vision API not available. Use --backend openai or --backend google with image-containing documents")
        
        prompt = REPORT_PROMPT_TEXT_ONLY.format(document_text=document_text, user_request=user_request)
        raw = llm_client.generate(prompt, max_tokens=4096)
    
    logging.info("LLM raw report response:\n%s", raw)
    result = parse_json_output(raw)
    
    # If user wants images but none suggested, force some images in sections
    if user_wants_images and extracted_images:
        sections = result.get("sections", [])
        images_assigned = set()
        for section in sections:
            if not section.get("images"):
                # Assign next available image
                for i in range(len(extracted_images)):
                    if i not in images_assigned:
                        section["images"] = [i]
                        images_assigned.add(i)
                        break
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Document-to-slide and report generation agent")
    parser.add_argument("--input", nargs='+', required=True, help="Path(s) to input file(s) or folder(s)")
    parser.add_argument("--mode", choices=["slides", "report", "both"], default="slides")
    parser.add_argument("--output-ppt", default="output.pptx", help="Output PowerPoint file path")
    parser.add_argument("--output-docx", default="output.docx", help="Output report file path")
    parser.add_argument("--template", help="Optional PowerPoint template path")
    parser.add_argument("--slide-request", default="Create a presentation from this material.", help="User request describing the desired slides")
    parser.add_argument("--report-request", default="Create a report from this material.", help="User request describing the desired report")
    parser.add_argument("--max-slides", type=int, default=DEFAULT_MAX_SLIDES, help="Maximum number of slides to generate")
    parser.add_argument("--backend", choices=["auto", "openai", "google", "transformers"], default="auto", help="LLM backend to use")
    parser.add_argument("--model-name", help="Optional model name for the transformer or Google backend")
    parser.add_argument("--image-mode", choices=["off", "ocr", "auto"], default="auto", help="How to handle embedded images: off (ignore), auto (use vision API if available), ocr (legacy: same as auto)")
    args = parser.parse_args()
    mode = args.mode
    if mode == "slides" and "--mode" not in sys.argv and any(arg.startswith("--report-request") for arg in sys.argv):
        mode = "report"
        logging.info("Detected --report-request without explicit --mode; switching to report mode")

    input_paths = [Path(p) for p in args.input]
    document_texts = []
    all_extracted_images = []
    for input_path in input_paths:
        if not input_path.exists():
            raise FileNotFoundError(f"Input path does not exist: {input_path}")
        doc_text, extracted_imgs = load_document(str(input_path))
        document_texts.append(doc_text)
        all_extracted_images.extend(extracted_imgs)
    document_text = "\n\n".join(document_texts)
    
    # Handle image-mode parameter
    if args.image_mode == "off":
        extracted_images = []
    else:
        # "auto" or "ocr" both use the extracted images directly
        # The LLM client will decide whether to use vision API
        extracted_images = all_extracted_images
        if extracted_images and args.image_mode == "ocr":
            logging.info("Image mode 'ocr' is legacy; switching to direct image ingestion with vision API")
    
    # Allow documents with text OR images (not requiring both)
    has_content = document_text.strip() or extracted_images
    if not has_content:
        raise ValueError("No content (text or images) could be extracted from the input document(s)")
    
    if extracted_images:
        logging.info("Extracted %d image(s) from document(s)", len(extracted_images))
    if document_text.strip():
        logging.info("Extracted text: %d characters", len(document_text.strip()))

    llm_client = LLMClient(model_name=args.model_name, backend=args.backend)

    if mode in {"slides", "both"}:
        slides = build_slides_content(document_text, extracted_images, args.slide_request, llm_client, args.max_slides)
        logging.info("Parsed slides: %s", json.dumps(slides, indent=2))
        builder = PresentationBuilder(template_path=args.template)
        builder.build_from_outline(slides, extracted_images)
        builder.save(args.output_ppt)
        logging.info("Generated presentation: %s", args.output_ppt)

    if mode in {"report", "both"}:
        report = build_report_content(document_text, extracted_images, args.report_request, llm_client)
        report_builder = ReportBuilder()
        report_builder.build(report, args.output_docx, extracted_images)
        logging.info("Generated report: %s", args.output_docx)


if __name__ == "__main__":
    main()
