"""
"Paper" theme: warm cream paper, ink colored text and a sienna accent.
Dark mode ("papel de noche") colors live in template.html and are generated
here only for the areas.
"""

import re
from typing import Dict, Tuple

PAGE = "#efe7da"  # around the sheet
PAPER = "#fbf7f0"
INK = "#3b2f2a"  # titles
BODY = "#4a3d36"  # running text
MUTED = "#8a7b6e"
RULE = "#e3d8c6"
DOT = "#d6c9b5"
ACCENT = "#a0522d"  # sienna
RED = "#b42318"
NOTE_BG = "#f3ebdd"
NOTE_RED_BG = "#fbe9e4"

SERIF = "Georgia,'Times New Roman',serif"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

# Area -> (ink color on paper, ink color on dark paper). Printed, muted tones.
AREA_STYLES: Dict[str, Tuple[str, str]] = {
    "Hogar": ("#9a6b1f", "#e2b46a"),
    "Gatos": ("#a3466e", "#e79abb"),
    "Carro": ("#4a5a8a", "#a3b2e0"),
    "Finanzas": ("#3f7a4f", "#8fcf9f"),
    "Trabajo": ("#2f6f86", "#86c6dc"),
    "Salud": ("#a33a3a", "#ec9a9a"),
    "Personal": ("#6b5d52", "#c4b4a5"),
    "Estudio": ("#b0602a", "#eba476"),
}
DEFAULT_AREA_STYLE = (MUTED, "#a89a8b")

# Agenda section key -> (title in the plain text, printed heading, color, class)
SECTION_STYLES = {
    "overdue": ("Vencidas", "Pendientes de días anteriores", RED, "red"),
    "today": ("Hoy", "Para hoy", ACCENT, "accent"),
    "upcoming": ("Próximos días", "Lo que viene", MUTED, "muted"),
}
ROMAN = ["I", "II", "III"]


def area_color(area: str) -> str:
    return AREA_STYLES.get(area, DEFAULT_AREA_STYLE)[0]


def area_class(area: str) -> str:
    """ "Finanzas" -> "tag-finanzas" (ASCII, safe as a CSS class)."""
    ascii_name = (
        area.lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    return "tag-" + re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")


def dark_area_css() -> str:
    return "\n".join(
        f"    .{area_class(name)} {{ color: {dark} !important; }}"
        for name, (_, dark) in AREA_STYLES.items()
    )
