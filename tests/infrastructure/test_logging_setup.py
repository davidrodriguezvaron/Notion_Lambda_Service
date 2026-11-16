import logging
import unittest

from app.infrastructure.logging_setup import configure_logging


class TestConfigureLogging(unittest.TestCase):
    def setUp(self):
        self.root = logging.getLogger()
        self.saved = (self.root.level, list(self.root.handlers))

    def tearDown(self):
        self.root.setLevel(self.saved[0])
        self.root.handlers[:] = self.saved[1]

    def test_adds_a_handler_when_none_exists(self):
        self.root.handlers[:] = []
        configure_logging("DEBUG")
        self.assertEqual(self.root.level, logging.DEBUG)
        self.assertEqual(len(self.root.handlers), 1)
        self.assertIsNotNone(self.root.handlers[0].formatter)

    def test_reuses_existing_handlers(self):
        handler = logging.StreamHandler()
        self.root.handlers[:] = [handler]
        configure_logging("WARNING")
        self.assertEqual(self.root.handlers, [handler])
        self.assertEqual(handler.level, logging.WARNING)


if __name__ == "__main__":
    unittest.main()
