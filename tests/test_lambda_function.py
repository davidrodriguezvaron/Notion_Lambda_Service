import os
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.application.send_daily_digest import DigestResult
from app.lambda_function import cached_use_case, lambda_handler, to_response
from tests.fakes import BASE_ENV

# 11 p. m. on Monday 16 Nov in Bogota (already 17 Nov in UTC).
LATE_NIGHT_UTC = datetime(2026, 11, 17, 4, 0, tzinfo=timezone.utc)


def page(page_id, title, due, recurrence=None):
    properties = {
        "Tarea": {"title": [{"plain_text": title}]},
        "Fecha": {"date": {"start": due}},
    }
    if recurrence:
        properties["Recurrencia"] = {"select": {"name": recurrence}}
    return {
        "id": page_id,
        "url": f"https://www.notion.so/{page_id}",
        "properties": properties,
    }


class FakeNotionSession:
    """Answers Notion HTTP calls: done recurring tasks vs pending tasks."""

    def __init__(self, pending=(), done=()):
        self.pending, self.done = list(pending), list(done)
        self.calls = []

    def request(self, method, url, headers, json, timeout):
        self.calls.append((method, url, json))
        response = MagicMock()
        if method == "PATCH":
            response.json.return_value = {}
        elif "'Done'" in str(json["filter"]):
            response.json.return_value = {"results": self.done, "has_more": False}
        else:
            response.json.return_value = {"results": self.pending, "has_more": False}
        return response


class TestLambdaHandlerEndToEnd(unittest.TestCase):
    def setUp(self):
        cached_use_case.cache_clear()

    def run_handler(self, session, **env):
        self.ses = MagicMock()
        with patch.dict(os.environ, dict(BASE_ENV, **env), clear=True), patch(
            "app.bootstrap.boto3.client", return_value=self.ses
        ), patch(
            "app.infrastructure.notion.client.requests.Session", return_value=session
        ), patch(
            "app.application.clock.utc_now", return_value=LATE_NIGHT_UTC
        ):
            return lambda_handler({}, None)

    def test_sends_the_digest_using_the_local_date(self):
        session = FakeNotionSession(pending=[page("1", "Pagar ENEL", "2026-11-16")])
        response = self.run_handler(session)

        self.assertEqual(response["statusCode"], 200)
        self.assertTrue(response["body"]["email_sent"])
        self.assertEqual(response["body"]["tasks"], 1)
        email = self.ses.send_email.call_args.kwargs
        # Due on 16 Nov is "today" at 11 p. m. in Bogota, not overdue.
        self.assertEqual(email["Message"]["Subject"]["Data"], "Tareas: 1 hoy")
        self.assertEqual(email["Source"], "sender@example.com")
        self.assertEqual(
            email["Destination"], {"ToAddresses": ["receiver@example.com"]}
        )
        self.assertIn("HOY (1)", email["Message"]["Body"]["Text"]["Data"])
        pending_query = session.calls[-1][2]
        self.assertEqual(
            pending_query["filter"]["and"][1]["date"]["on_or_before"], "2026-11-20"
        )

    def test_empty_day_succeeds_without_email(self):
        response = self.run_handler(FakeNotionSession())
        self.assertFalse(response["body"]["email_sent"])
        self.assertIn("email skipped", response["body"]["message"])
        self.ses.send_email.assert_not_called()

    def test_empty_day_sends_a_short_email_when_enabled(self):
        response = self.run_handler(FakeNotionSession(), SEND_EMPTY_DIGEST="true")
        self.assertTrue(response["body"]["email_sent"])
        subject = self.ses.send_email.call_args.kwargs["Message"]["Subject"]["Data"]
        self.assertEqual(subject, "Tareas: nada pendiente hoy")

    def test_recurring_done_task_is_reopened_and_reported(self):
        session = FakeNotionSession(
            done=[page("9", "Pagar ENEL", "2026-11-14", recurrence="Mensual")]
        )
        response = self.run_handler(session)

        patch_call = next(c for c in session.calls if c[0] == "PATCH")
        self.assertTrue(patch_call[1].endswith("/pages/9"))
        self.assertEqual(
            patch_call[2]["properties"]["Fecha"]["date"]["start"], "2026-12-14"
        )
        self.assertEqual(response["body"]["rescheduled"], 1)
        text = self.ses.send_email.call_args.kwargs["Message"]["Body"]["Text"]["Data"]
        self.assertIn("Pagar ENEL: del 14 nov al 14 dic", text)


class TestLambdaHandlerFailures(unittest.TestCase):
    def setUp(self):
        cached_use_case.cache_clear()

    def test_use_case_is_reused_across_warm_invocations(self):
        use_case = MagicMock()
        with patch.dict(os.environ, BASE_ENV, clear=True), patch(
            "app.lambda_function.build_send_daily_digest", return_value=use_case
        ) as build, patch("app.lambda_function.to_response"):
            lambda_handler({}, None)
            lambda_handler({}, None)
        build.assert_called_once()

    def test_invalid_environment_fails_the_invocation(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "app.config.settings.os.path.exists", return_value=False
        ):
            with self.assertRaises(ValueError) as cm:
                lambda_handler({}, None)
        self.assertIn("Missing required environment variables", str(cm.exception))

    def test_errors_are_re_raised(self):
        use_case = MagicMock()
        use_case.execute.side_effect = RuntimeError("Test error")
        with patch.dict(os.environ, BASE_ENV, clear=True), patch(
            "app.lambda_function.build_send_daily_digest", return_value=use_case
        ):
            with self.assertRaises(RuntimeError):
                lambda_handler({}, None)


class TestToResponse(unittest.TestCase):
    def test_sent(self):
        body = to_response(DigestResult(True, "Tareas: 1 hoy", 1, 0), "TEST")["body"]
        self.assertEqual(
            body["message"],
            "Process executed successfully from NotionLambda in TEST environment. "
            "Email sent: Tareas: 1 hoy",
        )


if __name__ == "__main__":
    unittest.main()
