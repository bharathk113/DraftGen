from docx import Document


class ReportBuilder:
    def build(self, report_json, output_path: str):
        doc = Document()
        title = report_json.get("title", "Generated Report")
        doc.add_heading(title, level=0)

        sections = report_json.get("sections", [])
        for section in sections:
            heading = section.get("heading")
            content = section.get("content", "")

            if heading:
                doc.add_heading(heading, level=1)

            if isinstance(content, list):
                for paragraph in content:
                    doc.add_paragraph(str(paragraph))
            else:
                for paragraph in str(content).split("\n\n"):
                    text = paragraph.strip()
                    if text:
                        doc.add_paragraph(text)

        doc.save(output_path)
