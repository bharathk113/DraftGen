import argparse
import json
import logging
import os
import sys
from pathlib import Path

from document_loader import load_document
from llm_client import LLMClient
from presentation_builder import PresentationBuilder
from report_builder import ReportBuilder

logging.basicConfig(level=logging.INFO, format="%(message)s")

DEFAULT_MAX_SLIDES = 30

SLIDE_PROMPT = """You are a helpful assistant that creates slide outlines from document content.

Input Document:
{document_text}

{image_section}

User Request:
{user_request}

Generate a JSON object with the key `slides` containing a list of slides. Each slide should include:
- `title` (a slide heading)
- `bullets` (a list of short bullet points; do not put title text here)
- optional `notes`

Ensure `title` is only the slide title and `bullets` are only bullet text.
Do not include any explanation outside the JSON object.
"""

REPORT_PROMPT = """You are a helpful assistant that writes a structured report from document content.

Input Document:
{document_text}

{image_section}

User Request:
{user_request}

Generate a JSON object with the keys `title` and `sections`. Each section should include:
- `heading`
- `content` (a paragraph or list of paragraphs)

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


def build_slides_content(document_text, image_descriptions, user_request, llm_client, max_slides):
    image_section = f"Embedded images:\n{chr(10).join(image_descriptions)}" if image_descriptions else ""
    prompt = SLIDE_PROMPT.format(document_text=document_text, image_section=image_section, user_request=user_request)
    raw = llm_client.generate(prompt, max_tokens=1000000)
    logging.info("LLM raw slide response:\n%s", raw)
    result = parse_json_output(raw)
    slides = result.get("slides", [])
    if len(slides) > max_slides:
        logging.info("Truncating slides from %d to %d", len(slides), max_slides)
        slides = slides[:max_slides]
    return slides


def build_report_content(document_text, image_descriptions, user_request, llm_client):
    image_section = f"Embedded images:\n{chr(10).join(image_descriptions)}" if image_descriptions else ""
    prompt = REPORT_PROMPT.format(document_text=document_text, image_section=image_section, user_request=user_request)
    raw = llm_client.generate(prompt, max_tokens=1024)
    logging.info("LLM raw report response:\n%s", raw)
    result = parse_json_output(raw)
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
    parser.add_argument("--image-mode", choices=["off", "ocr", "auto"], default="auto", help="How to handle embedded images: off (ignore), ocr (extract text), auto (ocr if available)")
    args = parser.parse_args()
    mode = args.mode
    if mode == "slides" and "--mode" not in sys.argv and any(arg.startswith("--report-request") for arg in sys.argv):
        mode = "report"
        logging.info("Detected --report-request without explicit --mode; switching to report mode")

    input_paths = [Path(p) for p in args.input]
    document_texts = []
    all_image_descriptions = []
    for input_path in input_paths:
        if not input_path.exists():
            raise FileNotFoundError(f"Input path does not exist: {input_path}")
        doc_text, img_descs = load_document(str(input_path))
        document_texts.append(doc_text)
        all_image_descriptions.extend(img_descs)
    document_text = "\n\n".join(document_texts)
    image_descriptions = all_image_descriptions if args.image_mode != "off" else []
    if not document_text.strip():
        raise ValueError("No text content could be extracted from the input document(s)")

    llm_client = LLMClient(model_name=args.model_name, backend=args.backend)

    if mode in {"slides", "both"}:
        slides = build_slides_content(document_text, image_descriptions, args.slide_request, llm_client, args.max_slides)
        logging.info("Parsed slides: %s", json.dumps(slides, indent=2))
        builder = PresentationBuilder(template_path=args.template)
        builder.build_from_outline(slides)
        builder.save(args.output_ppt)
        logging.info("Generated presentation: %s", args.output_ppt)

    if mode in {"report", "both"}:
        report = build_report_content(document_text, image_descriptions, args.report_request, llm_client)
        report_builder = ReportBuilder()
        report_builder.build(report, args.output_docx)
        logging.info("Generated report: %s", args.output_docx)


if __name__ == "__main__":
    main()
