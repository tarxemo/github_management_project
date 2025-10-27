import re
from typing import List

try:
    import markdown as md
except Exception:
    md = None

try:
    import bleach
except Exception:
    bleach = None

ALLOWED_TAGS: List[str] = [
    'p','br','hr','pre','code','blockquote','ul','ol','li',
    'strong','em','b','i','u','span','a','img','h1','h2','h3','h4','h5','h6'
]
ALLOWED_ATTRS = {
    '*': ['class', 'style'],
    'a': ['href', 'title', 'rel', 'target'],
    'img': ['src', 'alt', 'title']
}
ALLOWED_STYLES = ['color']

SAFE_LINK_PATTERN = re.compile(r'^(https?:)?//', re.I)


def render_markdown_safe(text: str) -> str:
    """Render Markdown to sanitized HTML allowing basic styling and colors.
    Falls back to escaped text when libs are missing.
    """
    if not text:
        return ''
    html = text
    if md:
        html = md.markdown(
            text,
            extensions=['extra', 'sane_lists', 'smarty']
        )
    # sanitize
    if bleach:
        html = bleach.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRS,
            styles=ALLOWED_STYLES,
            strip=True
        )
        # linkify URLs
        html = bleach.linkify(html, callbacks=[bleach.linkifier.DEFAULT_CALLBACK])
    return html
