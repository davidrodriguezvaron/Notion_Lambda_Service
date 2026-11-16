import unittest
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.application.clock import ZonedClock, utc_now

# 11 p. m. on 16 Nov in Bogota is already 17 Nov in UTC.
LATE_NIGHT_UTC = datetime(2026, 11, 17, 4, 0, tzinfo=timezone.utc)


class TestZonedClock(unittest.TestCase):
    def test_11pm_in_bogota_is_still_the_same_day(self):
        clock = ZonedClock(ZoneInfo("America/Bogota"), lambda: LATE_NIGHT_UTC)
        self.assertEqual(clock.today(), date(2026, 11, 16))
        self.assertEqual(LATE_NIGHT_UTC.date(), date(2026, 11, 17))

    def test_other_time_zone(self):
        clock = ZonedClock(ZoneInfo("Europe/Madrid"), lambda: LATE_NIGHT_UTC)
        self.assertEqual(clock.today(), date(2026, 11, 17))

    def test_real_clock(self):
        self.assertIsInstance(ZonedClock(ZoneInfo("UTC")).today(), date)
        self.assertIsNotNone(utc_now().tzinfo)


if __name__ == "__main__":
    unittest.main()
