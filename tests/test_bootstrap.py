import unittest
from unittest.mock import patch

from app.application.send_daily_digest import SendDailyDigest
from app.bootstrap import build_send_daily_digest
from app.config.settings import Settings
from tests.fakes import BASE_ENV


class TestBootstrap(unittest.TestCase):
    @patch("app.bootstrap.boto3.client")
    def test_wires_the_use_case_from_settings(self, boto_client):
        settings = Settings.from_env(dict(BASE_ENV, AWS_REGION="us-west-2"))

        use_case = build_send_daily_digest(settings)

        self.assertIsInstance(use_case, SendDailyDigest)
        boto_client.assert_called_once_with("ses", region_name="us-west-2")


if __name__ == "__main__":
    unittest.main()
