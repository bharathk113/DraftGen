from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.util import Inches, Pt

class PresentationBuilder:
    def __init__(self, template_path: str | None = None):
        self.prs = Presentation(template_path) if template_path else Presentation()
        self.default_layout = self._find_layout()

    def _find_layout(self):
        if len(self.prs.slide_layouts) > 1:
            return self.prs.slide_layouts[1]  # Usually title and content
        return self.prs.slide_layouts[0]

    def build_from_outline(self, slides):
        for slide_data in slides:
            title = slide_data.get("title", "Untitled Slide")
            bullets = slide_data.get("bullets", [])
            if isinstance(bullets, str):
                bullets = [b.strip() for b in bullets.split('\n') if b.strip()]
            notes = slide_data.get("notes", "")
            
            slide = self.prs.slides.add_slide(self.default_layout)

            # 1. Set Title Safely
            title_shape = slide.shapes.title
            if title_shape:
                title_shape.text = title

            # 2. Find Content/Body Placeholder
            body = None
            for placeholder in slide.placeholders:
                if placeholder.placeholder_format.type in {PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT}:
                    body = placeholder
                    break

            if body is None:
                for shape in slide.shapes:
                    is_title = title_shape and shape.shape_id == title_shape.shape_id
                    if getattr(shape, "has_text_frame", False) and not is_title:
                        body = shape
                        break

            # 3. Add Bullets and Adjust Sizes
            if body and bullets:
                tf = body.text_frame
                
                # -- ENABLE NATIVE POWERPOINT AUTOFIT --
                tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
                tf.word_wrap = True
                
                # -- DYNAMIC FONT SIZING CALCULATION --
                # Count total characters across all bullets in this slide
                total_chars = sum(len(str(b)) for b in bullets)
                
                # Thresholds: Adjust these Pt values if you want it larger or smaller
                if total_chars < 150:
                    calculated_size = Pt(28)
                elif total_chars < 250:
                    calculated_size = Pt(24)
                elif total_chars < 350:
                    calculated_size = Pt(20)
                else:
                    calculated_size = Pt(16)

                # Write first bullet
                p = tf.paragraphs[0]
                p.text = str(bullets[0])
                if p.runs:
                    p.runs[0].font.size = calculated_size
                
                # Write subsequent bullets
                for bullet in bullets[1:]:
                    p = tf.add_paragraph()
                    p.text = str(bullet)
                    p.level = 0
                    if p.runs:
                        p.runs[0].font.size = calculated_size

            # 4. Add Notes
            if notes:
                slide.notes_slide.notes_text_frame.text = notes

    def save(self, output_path: str):
        self.prs.save(output_path)