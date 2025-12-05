import unittest
from app.common.adapter.email_adapter import EmailAdapter


class TestEmailAdapter(unittest.TestCase):
    """Test cases for EmailAdapter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_tasks = [
            {
                "id": "task-1",
                "titulo": "Test Task 1",
                "fecha": "2024-11-24",
                "notas": "Some notes here",
            },
            {
                "id": "task-2",
                "titulo": "Test Task 2",
                "fecha": "2024-12-01",
                "notas": "",
            },
        ]
        self.adapter = EmailAdapter()

    def test_init_creates_adapter(self):
        """Test that __init__ creates an EmailAdapter instance."""
        adapter = EmailAdapter()
        self.assertIsInstance(adapter, EmailAdapter)

    def test_convert_to_email_format_returns_tuple(self):
        """Test that convert_to_email_format returns a tuple of strings."""
        subject, body = self.adapter.convert_to_email_format(self.sample_tasks)
        self.assertIsInstance(subject, str)
        self.assertIsInstance(body, str)

    def test_convert_to_email_format_contains_task_count(self):
        """Test that output contains the correct task count."""
        subject, body = self.adapter.convert_to_email_format(self.sample_tasks)
        self.assertIn("2 pending items", body)
        self.assertIn("2 Items Pending", subject)

    def test_convert_to_email_format_singular_item(self):
        """Test that output uses 'item' for single task."""
        subject, body = self.adapter.convert_to_email_format([self.sample_tasks[0]])
        self.assertIn("1 pending item", body)
        self.assertIn("1 Item Pending", subject)

    def test_convert_to_email_format_contains_task_titles(self):
        """Test that output contains task titles."""
        _, body = self.adapter.convert_to_email_format(self.sample_tasks)
        self.assertIn("Test Task 1", body)
        self.assertIn("Test Task 2", body)

    def test_convert_to_email_format_contains_formatted_dates(self):
        """Test that output contains formatted dates."""
        _, body = self.adapter.convert_to_email_format(self.sample_tasks)
        self.assertIn("Nov 24", body)
        self.assertIn("Dec 01", body)

    def test_convert_to_email_format_contains_notes(self):
        """Test that output contains task notes."""
        _, body = self.adapter.convert_to_email_format(self.sample_tasks)
        self.assertIn("Some notes here", body)

    def test_generate_task_rows_returns_html(self):
        """Test that _generate_task_rows returns HTML string."""
        result = self.adapter._generate_task_rows(self.sample_tasks)
        self.assertIn("<tr", result)
        self.assertIn("task-row", result)

    def test_generate_task_row_contains_date_pill(self):
        """Test that task row contains date pill element."""
        task = self.sample_tasks[0]
        result = self.adapter._generate_task_row(task)
        self.assertIn("date-pill", result)
        self.assertIn("Nov 24", result)

    def test_generate_task_row_contains_title(self):
        """Test that task row contains task title."""
        task = self.sample_tasks[0]
        result = self.adapter._generate_task_row(task)
        self.assertIn("task-title", result)
        self.assertIn("Test Task 1", result)

    def test_generate_task_row_contains_notes_when_present(self):
        """Test that task row contains notes when provided."""
        task = self.sample_tasks[0]
        result = self.adapter._generate_task_row(task)
        self.assertIn("task-notes", result)
        self.assertIn("Some notes here", result)

    def test_generate_task_row_excludes_notes_when_empty(self):
        """Test that task row excludes notes section when notes are empty."""
        task = self.sample_tasks[1]
        result = self.adapter._generate_task_row(task)
        self.assertNotIn("task-notes", result)

    def test_generate_notes_html_escapes_special_characters(self):
        """Test that notes HTML escapes special characters."""
        result = self.adapter._generate_notes_html("<script>alert('xss')</script>")
        self.assertIn("&lt;script&gt;", result)
        self.assertNotIn("<script>", result)

    def test_generate_notes_html_converts_urls_to_links(self):
        """Test that URLs in notes are converted to links."""
        result = self.adapter._generate_notes_html("Check https://example.com")
        self.assertIn('<a href="https://example.com"', result)
        self.assertIn("link-text", result)

    def test_generate_notes_html_converts_www_urls(self):
        """Test that www URLs are converted to links with https."""
        result = self.adapter._generate_notes_html("Visit www.example.com")
        self.assertIn('<a href="https://www.example.com"', result)
        self.assertIn("www.example.com</a>", result)

    def test_format_date_returns_formatted_string(self):
        """Test that _format_date returns 'Mon DD' format."""
        result = self.adapter._format_date("2024-11-24")
        self.assertEqual(result, "Nov 24")

    def test_format_date_returns_no_date_for_none(self):
        """Test that _format_date returns 'No Date' for None."""
        result = self.adapter._format_date(None)
        self.assertEqual(result, "No Date")

    def test_format_date_returns_invalid_for_bad_format(self):
        """Test that _format_date returns 'Invalid' for invalid date."""
        result = self.adapter._format_date("invalid-date")
        self.assertEqual(result, "Invalid")

    def test_format_date_handles_different_months(self):
        """Test that _format_date handles different months correctly."""
        self.assertEqual(self.adapter._format_date("2024-01-15"), "Jan 15")
        self.assertEqual(self.adapter._format_date("2024-06-30"), "Jun 30")
        self.assertEqual(self.adapter._format_date("2024-12-25"), "Dec 25")

    def test_load_template_returns_string(self):
        """Test that _load_template returns template content."""
        result = self.adapter._load_template()
        self.assertIsInstance(result, str)
        self.assertIn("<!DOCTYPE html>", result)

    def test_load_template_contains_placeholders(self):
        """Test that template contains expected placeholders."""
        result = self.adapter._load_template()
        self.assertIn("{{task_count}}", result)
        self.assertIn("{{item_word}}", result)
        self.assertIn("{{task_rows}}", result)
        self.assertIn("{{year}}", result)

    def test_convert_to_email_format_replaces_all_placeholders(self):
        """Test that all placeholders are replaced in final output."""
        _, body = self.adapter.convert_to_email_format(self.sample_tasks)
        self.assertNotIn("{{task_count}}", body)
        self.assertNotIn("{{item_word}}", body)
        self.assertNotIn("{{task_rows}}", body)
        self.assertNotIn("{{year}}", body)

    def test_convert_to_email_format_contains_current_year(self):
        """Test that output contains the current year."""
        from datetime import datetime

        _, body = self.adapter.convert_to_email_format(self.sample_tasks)
        self.assertIn(str(datetime.now().year), body)

    def test_convert_to_email_format_empty_tasks(self):
        """Test that output is valid with empty tasks list."""
        _, body = self.adapter.convert_to_email_format([])
        self.assertIn("0 pending items", body)
        self.assertIn("<!DOCTYPE html>", body)

    def test_title_escapes_html_entities(self):
        """Test that task titles are HTML escaped."""
        tasks = [
            {"id": "1", "titulo": "<b>Bold</b>", "fecha": "2024-12-05", "notas": ""}
        ]
        _, body = self.adapter.convert_to_email_format(tasks)
        self.assertIn("&lt;b&gt;Bold&lt;/b&gt;", body)
        self.assertNotIn("<b>Bold</b>", body)

    def test_adapter_is_reusable(self):
        """Test that the same adapter instance can be reused with different tasks."""
        subject1, body1 = self.adapter.convert_to_email_format([self.sample_tasks[0]])
        subject2, body2 = self.adapter.convert_to_email_format([self.sample_tasks[1]])

        self.assertIn("Test Task 1", body1)
        self.assertNotIn("Test Task 2", body1)
        self.assertIn("Item", subject1)

        self.assertIn("Test Task 2", body2)
        self.assertNotIn("Test Task 1", body2)
        self.assertIn("Item", subject2)


if __name__ == "__main__":
    unittest.main()
