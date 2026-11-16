import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from app.logic.function.function import NotionLambda
from app.logic.recurrence.recurrence_service import RecurrenceResult, Rescheduled

# 23:00 on 16 Nov in Bogota (already 17 Nov in UTC).
NOW = datetime(2026, 11, 17, 4, 0, tzinfo=timezone.utc)


def notion_page(page_id, title, fecha):
    return {
        "id": page_id,
        "url": f"https://www.notion.so/{page_id}",
        "properties": {
            "Tarea": {"title": [{"plain_text": title}]},
            "Fecha": {"date": {"start": fecha}},
        },
    }


class TestNotionLambda(unittest.TestCase):
    def setUp(self):
        env_patcher = patch("app.logic.function.function.environment_handler")
        ses_patcher = patch("app.logic.function.function.SesClient")
        self.env = env_patcher.start()
        ses_class = ses_patcher.start()
        self.addCleanup(env_patcher.stop)
        self.addCleanup(ses_patcher.stop)

        self.env.ses_sender_and_receiver = (
            "sender@example.com",
            "receiver@example.com",
        )
        self.env.notion_database_id = "db"
        self.env.environment = "TEST"
        self.env.notion_database_filter_properties = "Notas,Tarea,Fecha"
        self.env.timezone = ZoneInfo("America/Bogota")
        self.env.timezone_name = "America/Bogota"
        self.env.upcoming_days = 3
        self.env.send_empty_digest = False
        self.env.notion_tasks_url = "https://www.notion.so/db"
        self.ses = ses_class.return_value

        self.client = Mock()
        self.pending_pages = [notion_page("1", "Pagar ENEL", "2026-11-16")]
        self.done_pages = []

        def post(endpoint, payload):
            statuses = str(payload["filter"])
            results = self.done_pages if "'Done'" in statuses else self.pending_pages
            return {"results": results, "has_more": False}

        self.client.post.side_effect = post
        self.lambda_ = NotionLambda(self.client)

    def test_init_uses_environment_handler(self):
        self.assertEqual(self.lambda_.env_handler, self.env)
        self.assertEqual(self.lambda_.notion_client, self.client)

    def test_sends_digest_using_local_date(self):
        response = self.lambda_.notion_lambda_function(now=NOW)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["Content-Type"], "application/json")
        self.assertTrue(response["body"]["email_sent"])
        self.assertIn("Process executed successfully", response["body"]["message"])

        kwargs = self.ses.send_email.call_args.kwargs
        # The task dated 16 Nov is "today" at 11 p. m. in Bogota, not overdue.
        self.assertEqual(kwargs["subject"], "Tareas: 1 hoy")
        self.assertEqual(kwargs["sender"], "sender@example.com")
        self.assertEqual(kwargs["receiver"], ["receiver@example.com"])
        self.assertIn("Lunes, 16 de noviembre", kwargs["body"])
        self.assertIn("HOY (1)", kwargs["text_body"])

        pending_payload = self.client.post.call_args_list[-1][0][1]
        self.assertEqual(
            pending_payload["filter"]["and"][1]["date"]["on_or_before"], "2026-11-20"
        )

    def test_no_tasks_succeeds_without_email(self):
        self.pending_pages = []
        response = self.lambda_.notion_lambda_function(now=NOW)

        self.assertEqual(response["statusCode"], 200)
        self.assertFalse(response["body"]["email_sent"])
        self.ses.send_email.assert_not_called()

    def test_no_tasks_sends_short_email_when_enabled(self):
        self.pending_pages = []
        self.env.send_empty_digest = True
        response = self.lambda_.notion_lambda_function(now=NOW)

        self.assertTrue(response["body"]["email_sent"])
        kwargs = self.ses.send_email.call_args.kwargs
        self.assertEqual(kwargs["subject"], "Tareas: nada pendiente hoy")
        self.assertIn("Nada pendiente hoy", kwargs["body"])

    def test_recurrence_runs_before_the_digest(self):
        self.lambda_.recurrence_service = Mock()
        self.lambda_.recurrence_service.process.return_value = RecurrenceResult(
            rescheduled=[Rescheduled("Pagar Vanti", datetime(2026, 12, 21).date())],
            warnings=[],
        )
        response = self.lambda_.notion_lambda_function(now=NOW)

        self.assertEqual(response["body"]["rescheduled"], 1)
        body = self.ses.send_email.call_args.kwargs["body"]
        self.assertIn("Pagar Vanti al 21 dic", body)

    def test_recurring_done_task_is_patched(self):
        page = notion_page("9", "Pagar ENEL", "2026-11-14")
        page["properties"]["Recurrencia"] = {"select": {"name": "Mensual"}}
        self.done_pages = [page]
        self.lambda_.notion_lambda_function(now=NOW)

        self.client.patch.assert_called_once()
        endpoint, payload = self.client.patch.call_args[0]
        self.assertEqual(endpoint, "pages/9")
        self.assertEqual(payload["properties"]["Fecha"]["date"]["start"], "2026-12-14")


if __name__ == "__main__":
    unittest.main()
