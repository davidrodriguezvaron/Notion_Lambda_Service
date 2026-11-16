import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.domain.task import DueDate, Task, format_time

BOGOTA = ZoneInfo("America/Bogota")


class TestDueDate(unittest.TestCase):
    def test_plain_date(self):
        result = DueDate.parse("2026-11-16", BOGOTA)
        self.assertEqual(result, DueDate(date(2026, 11, 16)))

    def test_datetime_with_offset(self):
        result = DueDate.parse("2026-11-16T10:30:00.000-05:00", BOGOTA)
        self.assertEqual(result, DueDate(date(2026, 11, 16), "10:30 a. m."))

    def test_utc_datetime_is_converted_to_the_local_day(self):
        # 03:00 UTC on 17 Nov is 10 p. m. on 16 Nov in Bogota.
        result = DueDate.parse("2026-11-17T03:00:00.000Z", BOGOTA)
        self.assertEqual(result, DueDate(date(2026, 11, 16), "10:00 p. m."))

    def test_naive_datetime_uses_the_configured_zone(self):
        self.assertEqual(
            DueDate.parse("2026-11-16T08:05:00", BOGOTA).time, "8:05 a. m."
        )

    def test_empty_and_invalid(self):
        for value in (None, "", "no-es-fecha", "2026-13-40T10:00"):
            with self.subTest(value=value):
                self.assertIsNone(DueDate.parse(value, BOGOTA))

    def test_invalid_value_is_logged(self):
        with self.assertLogs("app.domain.task", level="WARNING"):
            DueDate.parse("no-es-fechaT", BOGOTA)


class TestFormatTime(unittest.TestCase):
    def test_noon_and_midnight(self):
        self.assertEqual(format_time(datetime(2026, 1, 1, 12, 0)), "12:00 p. m.")
        self.assertEqual(format_time(datetime(2026, 1, 1, 0, 15)), "12:15 a. m.")


class TestTask(unittest.TestCase):
    def test_due_date_uses_the_raw_value(self):
        item = Task(id="1", title="x", due="2026-11-16T10:30:00-05:00")
        self.assertEqual(item.due_date(BOGOTA).time, "10:30 a. m.")

    def test_without_due_date(self):
        self.assertIsNone(Task(id="1", title="x").due_date(BOGOTA))


if __name__ == "__main__":
    unittest.main()
