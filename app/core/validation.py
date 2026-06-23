"""
Input validation and sanitization helpers.

Used for user-supplied strings that end up in HTML content rendered in the BI UI.
"""
import re

_SCRIPT_RE = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
_EVENT_RE = re.compile(r'''\s+on\w+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)''', re.IGNORECASE)
_IFRAME_SCRIPT_RE = re.compile(r'javascript\s*:', re.IGNORECASE)


def sanitize_html(html: str | None) -> str | None:
    """
    Strip obviously dangerous HTML from user-supplied content.

    Removes:
    - <script>...</script> blocks
    - inline event handlers (onclick=, onerror=, ...)
    - javascript: URIs

    Args:
        html: Input HTML string (may be None or empty)

    Returns:
        Cleaned HTML, or the original input if it was None/empty.
    """
    if not html:
        return html
    html = _SCRIPT_RE.sub('', html)
    html = _EVENT_RE.sub('', html)
    html = _IFRAME_SCRIPT_RE.sub('blocked:', html)
    return html
