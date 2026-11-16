"""Small HTML building blocks shared by the email renderers."""

import html

from app.presentation.email.theme import SANS


def attr(value: str) -> str:
    """Escapes a value for use inside an HTML attribute."""
    return html.escape(value or "", quote=True)


def row(content: str, padding: str) -> str:
    """One full width row of the paper sheet."""
    return f'<tr><td class="px" style="padding:{padding};">{content}</td></tr>'


def label(text: str, color: str, css_class: str, extra: str = "") -> str:
    """Small uppercase sans label, the "newspaper" section style."""
    return (
        f'<div class="{css_class}" style="font-family:{SANS};font-size:11px;'
        f"line-height:16px;letter-spacing:0.2em;text-transform:uppercase;"
        f'color:{color};{extra}">{text}</div>'
    )
