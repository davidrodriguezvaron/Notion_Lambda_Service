import unittest
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.common.utils.dates import (
    add_months,
    format_long_date,
    format_short_date,
    format_time,
    parse_notion_date,
    relative_label,
    today_in,
)

BOGOTA = ZoneInfo("America/Bogota")


class TestTodayIn(unittest.TestCase):
    def test_11pm_in_bogota_is_still_the_same_day(self):
        # 23:00 in Bogota on 16 Nov is 04:00 UTC on 17 Nov.
        now_utc = datetime(2026, 11, 17, 4, 0, tzinfo=timezone.utc)
        self.assertEqual(today_in(BOGOTA, now_utc), date(2026, 11, 16))
        self.assertEqual(now_utc.date(), date(2026, 11, 17))

    def test_uses_real_clock_when_now_is_none(self):
        self.assertIsInstance(today_in(BOGOTA), date)

    def test_other_time_zone(self):
        now_utc = datetime(2026, 11, 17, 4, 0, tzinfo=timezone.utc)
        self.assertEqual(
            today_in(ZoneInfo("Europe/Madrid"), now_utc), date(2026, 11, 17)
        )


class TestParseNotionDate(unittest.TestCase):
    def test_plain_date(self):
        result = parse_notion_date("2026-11-16", BOGOTA)
        self.assertEqual(result.day, date(2026, 11, 16))
        self.assertIsNone(result.time)

    def test_datetime_with_offset(self):
        result = parse_notion_date("2026-11-16T10:30:00.000-05:00", BOGOTA)
        self.assertEqual(result.day, date(2026, 11, 16))
        self.assertEqual(result.time, "10:30 a. m.")

    def test_utc_datetime_converted_to_local_day(self):
        # 03:00 UTC on 17 Nov is 10 p. m. on 16 Nov in Bogota.
        result = parse_notion_date("2026-11-17T03:00:00.000Z", BOGOTA)
        self.assertEqual(result.day, date(2026, 11, 16))
        self.assertEqual(result.time, "10:00 p. m.")

    def test_naive_datetime_uses_configured_zone(self):
        result = parse_notion_date("2026-11-16T08:05:00", BOGOTA)
        self.assertEqual(result.time, "8:05 a. m.")

    def test_empty_and_invalid(self):
        self.assertIsNone(parse_notion_date(None, BOGOTA))
        self.assertIsNone(parse_notion_date("", BOGOTA))
        self.assertIsNone(parse_notion_date("no-es-fecha", BOGOTA))


class TestFormatting(unittest.TestCase):
    def test_format_time_noon_and_midnight(self):
        self.assertEqual(format_time(datetime(2026, 1, 1, 12, 0)), "12:00 p. m.")
        self.assertEqual(format_time(datetime(2026, 1, 1, 0, 15)), "12:15 a. m.")

    def test_long_date_in_spanish(self):
        self.assertEqual(
            format_long_date(date(2026, 11, 15)), "Domingo, 15 de noviembre"
        )

    def test_short_date_in_spanish(self):
        self.assertEqual(format_short_date(date(2026, 11, 19)), "jue 19 nov")


class TestRelativeLabel(unittest.TestCase):
    today = date(2026, 11, 16)

    def test_labels(self):
        cases = {
            -5: "hace 5 días",
            -2: "hace 2 días",
            -1: "ayer",
            0: "hoy",
            1: "mañana",
            2: "en 2 días, mié 18 nov",
            3: "en 3 días, jue 19 nov",
        }
        for offset, expected in cases.items():
            target = date.fromordinal(self.today.toordinal() + offset)
            self.assertEqual(relative_label(target, self.today), expected)


class TestAddMonths(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(add_months(date(2026, 11, 21), 1), date(2026, 12, 21))

    def test_year_rollover(self):
        self.assertEqual(add_months(date(2026, 12, 15), 2), date(2027, 2, 15))

    def test_clamps_to_end_of_month(self):
        self.assertEqual(add_months(date(2027, 1, 31), 1), date(2027, 2, 28))
        self.assertEqual(add_months(date(2028, 1, 31), 1), date(2028, 2, 29))


if __name__ == "__main__":
    unittest.main()
