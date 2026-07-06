import io

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

styles = getSampleStyleSheet()


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


def render_memoir_pdf(memoir_markdown: str) -> bytes:
    """Renders the model's markdown memoir into a formatted PDF: a title
    page, then one chapter per page break with heading + prose paragraphs.
    """
    title, chapters = _parse_markdown(memoir_markdown)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    story = [
        Spacer(1, 200),
        Paragraph(title, styles["Title"]),
        Paragraph("A Memoir", styles["Italic"]),
    ]

    for heading, paragraphs in chapters:
        story.append(PageBreak())
        story.append(Paragraph(heading, styles["Heading1"]))
        story.append(Spacer(1, 12))
        for paragraph in paragraphs:
            story.append(Paragraph(paragraph, styles["BodyText"]))
            story.append(Spacer(1, 12))

    doc.build(story)
    return buffer.getvalue()
