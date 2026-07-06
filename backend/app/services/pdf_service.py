import io
from typing import Optional

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

styles = getSampleStyleSheet()

COVER_PHOTO_MAX_SIZE = 300


def _parse_markdown(memoir_markdown: str) -> tuple[str, list[tuple[str, list[str]]]]:
    """Splits the model's minimal markdown convention into a title and a
    list of (chapter_heading, paragraphs) tuples."""
    title = ""
    chapters: list[tuple[str, list[str]]] = []
    paragraph_buffer: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_buffer:
            chapters[-1][1].append(" ".join(paragraph_buffer))
            paragraph_buffer.clear()

    for raw_line in memoir_markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            flush_paragraph()
            chapters.append((line[3:].strip(), []))
        elif line:
            paragraph_buffer.append(line)
        else:
            flush_paragraph()
    flush_paragraph()

    return title, chapters


def _cover_photo_flowable(cover_photo_bytes: bytes) -> Image:
    image = Image(io.BytesIO(cover_photo_bytes))
    scale = min(
        COVER_PHOTO_MAX_SIZE / image.imageWidth,
        COVER_PHOTO_MAX_SIZE / image.imageHeight,
        1,
    )
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    image.hAlign = "CENTER"
    return image


def render_memoir_pdf(
    memoir_markdown: str, cover_photo_bytes: Optional[bytes] = None
) -> bytes:
    """Renders the model's markdown memoir into a formatted PDF: a title
    page (with an optional cover photo above the title), then one chapter
    per page break with heading + prose paragraphs.
    """
    title, chapters = _parse_markdown(memoir_markdown)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    story = [Spacer(1, 120 if cover_photo_bytes else 200)]
    if cover_photo_bytes:
        story.append(_cover_photo_flowable(cover_photo_bytes))
        story.append(Spacer(1, 24))
    story.append(Paragraph(title, styles["Title"]))
    story.append(Paragraph("A Memoir", styles["Italic"]))

    for heading, paragraphs in chapters:
        story.append(PageBreak())
        story.append(Paragraph(heading, styles["Heading1"]))
        story.append(Spacer(1, 12))
        for paragraph in paragraphs:
            story.append(Paragraph(paragraph, styles["BodyText"]))
            story.append(Spacer(1, 12))

    doc.build(story)
    return buffer.getvalue()
