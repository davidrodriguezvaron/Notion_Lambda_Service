"""Turns plain text notes into safe HTML with clickable links."""

import html
import re

from app.presentation.email.html_primitives import attr

URL_PATTERN = re.compile(r"(https?://[^\s<>\"']+|www\.[^\s<>\"']+)")
TRAILING_PUNCTUATION = ".,;:!?)]}"


def notes_to_html(notes: str, link_color: str, link_class: str) -> str:
    """Escapes the text, links URLs (without trailing punctuation) and keeps
    line breaks."""
    parts = []
    last = 0
    for match in URL_PATTERN.finditer(notes):
        url = match.group(1).rstrip(TRAILING_PUNCTUATION)
        parts.append(html.escape(notes[last : match.start()]))
        href = url if url.startswith("http") else f"https://{url}"
        parts.append(
            f'<a href="{attr(href)}" class="{link_class}" '
            f'style="color:{link_color};text-decoration:underline;">'
            f"{html.escape(url)}</a>"
        )
        last = match.start() + len(url)
    parts.append(html.escape(notes[last:]))
    return "".join(parts).replace("\n", "<br>")
