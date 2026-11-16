import unittest
from datetime import date

from app.domain.recurrence import add_months, is_supported, next_date, next_start


class TestNextDate(unittest.TestCase):
    def test_each_interval(self):
        base = date(2026, 11, 21)
        expected = {
            "Semanal": date(2026, 11, 28),
            "Quincenal": date(2026, 12, 5),
            "Mensual": date(2026, 12, 21),
            "Bimestral": date(2027, 1, 21),
            "Trimestral": date(2027, 2, 21),
            "Semestral": date(2027, 5, 21),
            "Anual": date(2027, 11, 21),
        }
        for interval, result in expected.items():
            with self.subTest(interval=interval):
                self.assertEqual(next_date(base, interval), result)

    def test_water_bill_every_two_months_from_3_dec(self):
        dates = [date(2026, 12, 3)]
        for _ in range(3):
            dates.append(next_date(dates[-1], "Bimestral"))
        self.assertEqual(
            dates,
            [date(2026, 12, 3), date(2027, 2, 3), date(2027, 4, 3), date(2027, 6, 3)],
        )

    def test_end_of_month_uses_the_last_day(self):
        self.assertEqual(next_date(date(2027, 1, 31), "Mensual"), date(2027, 2, 28))
        self.assertEqual(next_date(date(2028, 1, 31), "Mensual"), date(2028, 2, 29))
        self.assertEqual(next_date(date(2026, 8, 31), "Semestral"), date(2027, 2, 28))

    def test_year_rollover(self):
        self.assertEqual(next_date(date(2026, 12, 12), "Mensual"), date(2027, 1, 12))
        self.assertEqual(next_date(date(2027, 9, 1), "Anual"), date(2028, 9, 1))


class TestNextStart(unittest.TestCase):
    def test_plain_date(self):
        self.assertEqual(
            next_start("2026-11-21", "Mensual"),
            (date(2026, 11, 21), date(2026, 12, 21), "2026-12-21"),
        )

    def test_keeps_time_and_offset(self):
        _, _, value = next_start("2026-11-21T10:30:00.000-05:00", "Semanal")
        self.assertEqual(value, "2026-11-28T10:30:00.000-05:00")


class TestHelpers(unittest.TestCase):
    def test_is_supported(self):
        self.assertTrue(is_supported("Mensual"))
        self.assertFalse(is_supported("Cada luna llena"))
        self.assertFalse(is_supported(None))

    def test_add_months(self):
        self.assertEqual(add_months(date(2026, 12, 15), 2), date(2027, 2, 15))


if __name__ == "__main__":
    unittest.main()
