from django.template.loader import render_to_string
from django.conf import settings
from importlib import resources
from pathlib import Path


def _load_theme_css(theme_name: str) -> str:
    base = Path(settings.BASE_DIR) / 'badges' / 'templates' / 'badges' / 'themes'
    css_path = base / f'{theme_name}.css'
    if css_path.exists():
        return css_path.read_text(encoding='utf-8')
    # default
    default_path = base / 'cyberpunk.css'
    return default_path.read_text(encoding='utf-8') if default_path.exists() else ''


def render_svg_with_theme(template_name: str, context: dict) -> str:
    theme_css = _load_theme_css(context.get('theme_name', 'cyberpunk'))
    ctx = {**context, 'theme_css': theme_css}
    return render_to_string(template_name, ctx)


def try_render_png(svg_text: str):
    try:
        import cairosvg  # type: ignore
    except Exception:
        return None
    try:
        return cairosvg.svg2png(bytestring=svg_text.encode('utf-8'))
    except Exception:
        return None
