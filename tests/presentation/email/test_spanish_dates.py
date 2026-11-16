import unittest
from datetime import date

from app.presentation.email.spanish_dates import (
    format_day_month,
    format_long_date,
    format_month_year,
    format_short_date,
    format_weekday_day,
    relative_label,
    weekday_name,
)

TODAY = date(2026, 11, 16)


class TestSpanishDates(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(
            format_long_date(date(2026, 11, 15)), "Domingo, 15 de noviembre"
        )
        self.assertEqual(format_short_date(date(2026, 11, 19)), "jue 19 nov")
        self.assertEqual(format_weekday_day(date(2026, 11, 18)), "mié 18")
        self.assertEqual(format_day_month(date(2026, 12, 21)), "21 dic")
        self.assertEqual(format_month_year(TODAY), "de noviembre de 2026")
        self.assertEqual(weekday_name(TODAY), "lunes")

    def test_relative_labels(self):
        cases = {
            -5: "hace 5 días",
            -1: "ayer",
            0: "hoy",
            1: "mañana",
            2: "en 2 días, mié 18 nov",
            3: "en 3 días, jue 19 nov",
        }
        for offset, expected in cases.items():
            with self.subTest(offset=offset):
                target = date.fromordinal(TODAY.toordinal() + offset)
                self.assertEqual(relative_label(target, TODAY), expected)


if __name__ == "__main__":
    unittest.main()
