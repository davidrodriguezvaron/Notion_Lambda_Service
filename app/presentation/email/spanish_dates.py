"""
Spanish date formatting.

Day and month names are defined here on purpose: the Lambda runtime does not
ship the es_CO locale, so strftime("%A") would return English names.
"""

from datetime import date

DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DAYS_SHORT = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MONTHS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]
MONTHS_SHORT = [
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
]


def weekday_name(value: date) -> str:
    """ "lunes"."""
    return DAYS[value.weekday()]


def format_long_date(value: date) -> str:
    """ "Lunes, 16 de noviembre"."""
    return (
        f"{weekday_name(value).capitalize()}, {value.day} de {MONTHS[value.month - 1]}"
    )


def format_month_year(value: date) -> str:
    """ "de noviembre de 2026"."""
    return f"de {MONTHS[value.month - 1]} de {value.year}"


def format_weekday_day(value: date) -> str:
    """ "jue 19"."""
    return f"{DAYS_SHORT[value.weekday()]} {value.day}"


def format_short_date(value: date) -> str:
    """ "jue 19 nov"."""
    return f"{format_weekday_day(value)} {MONTHS_SHORT[value.month - 1]}"


def format_day_month(value: date) -> str:
    """ "21 dic"."""
    return f"{value.day} {MONTHS_SHORT[value.month - 1]}"


def relative_label(target: date, today: date) -> str:
    """
    Label relative to today: "hace 2 días", "ayer", "hoy", "mañana",
    "en 2 días, jue 19 nov".
    """
    delta = (target - today).days
    if delta == 0:
        return "hoy"
    if delta == -1:
        return "ayer"
    if delta < -1:
        return f"hace {-delta} días"
    if delta == 1:
        return "mañana"
    return f"en {delta} días, {format_short_date(target)}"
