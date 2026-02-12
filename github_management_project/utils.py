from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import Color

def add_logo_watermark(canvas, doc, logo_path, opacity=0.05, spacing=200, rotation=45):
    """
    Adds a repeating watermark with a logo at a given rotation and opacity across the PDF page.
    
    Args:
        canvas: The canvas object from ReportLab.
        doc: The document being created.
        logo_path: Path to the logo image file.
        opacity: Float between 0 and 1 for transparency.
        spacing: Space between watermarks horizontally and vertically.
        rotation: Rotation angle of the watermark.
    """
    canvas.saveState()
    
    # Load image once
    logo = ImageReader(logo_path)
    width, height = canvas._pagesize

    # Set transparency
    try:
        canvas.setFillAlpha(opacity)
    except AttributeError:
        # For older versions of ReportLab, use this hack
        canvas.setFillColor(Color(0, 0, 0, alpha=opacity))
    
    # Define size of the watermark image (adjust as needed)
    watermark_width = 100
    watermark_height = 100

    # Create tiled watermarks
    x = -spacing
    while x < width + spacing:
        y = -spacing
        while y < height + spacing:
            canvas.saveState()
            canvas.translate(x, y)
            canvas.rotate(rotation)
            canvas.drawImage(logo, 0, 0, width=watermark_width, height=watermark_height, mask='auto')
            canvas.restoreState()
            y += spacing
        x += spacing

    canvas.restoreState()

from reportlab.pdfgen import canvas as canvas_module
from reportlab.lib.colors import Color

def add_text_watermark(canvas, doc, text="Leonidas Farm", font_size=30, angle=45, opacity=0.05):
    from math import radians, cos, sin
    
    canvas.saveState()

    # Set custom fill color with opacity
    color = Color(0.5, 0.5, 0.5, alpha=opacity)
    canvas.setFillColor(color)
    canvas.setFont("Helvetica-Bold", font_size)

    page_width, page_height = doc.pagesize

    # Calculate diagonal step size based on font size
    step_x = step_y = font_size * 4

    # Precalculate sin and cos for angle
    angle_rad = radians(angle)
    cos_a = cos(angle_rad)
    sin_a = sin(angle_rad)

    # Calculate the number of rows and columns needed
    cols = int(page_width / step_x) + 2
    rows = int(page_height / step_y) + 2

    for row in range(rows):
        for col in range(cols):
            x = col * step_x
            y = row * step_y
            canvas.saveState()
            canvas.translate(x, y)
            canvas.rotate(angle)
            canvas.drawCentredString(0, 0, text)
            canvas.restoreState()

    canvas.restoreState()


def get_github_token():
    """
    Retrieve the next available GitHub token using round-robin.
    """
    from django.conf import settings
    from django.core.cache import cache

    tokens = settings.GITHUB_TOKENS
    if not tokens:
        raise ValueError("No GitHub tokens configured.")

    # Use cache to track the current token index
    cache_key = 'github_token_index'
    current_index = cache.get(cache_key, 0)

    # Get the token and update the index
    token = tokens[current_index]
    next_index = (current_index + 1) % len(tokens)
    cache.set(cache_key, next_index, timeout=None)

    return token


def sitewise_context(request):
    """
    Context processor to make SiteWise configuration available in templates.
    """
    from django.conf import settings
    return {
        'SITEWISE_API_KEY': settings.SITEWISE_API_KEY,
        'SITEWISE_BASE_URL': settings.SITEWISE_BASE_URL,
    }
