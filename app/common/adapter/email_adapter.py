import html
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class EmailAdapter:
    """
    Adapter to convert Notion tasks into HTML email format.

    This class generates styled HTML emails ready for sending via AWS SES.
    """

    TEMPLATE_PATH = (
        Path(__file__).parent.parent.parent / "resources" / "email_template.html"
    )

    def __init__(self):
        """Initializes the EmailAdapter."""
        self._template = None

    def convert_to_email_format(self, tasks: List[Dict[str, Any]]) -> tuple[str, str]:
        """
        Converts the list of tasks to an HTML email message and generates a subject.

        Args:
            tasks: List of task dictionaries.

        Returns:
            tuple[str, str]: A tuple containing (subject, html_body).
        """
        task_rows = self._generate_task_rows(tasks)
        task_count = len(tasks)
        item_word = "item" if task_count == 1 else "items"

        template = self._load_template()

        html_body = (
            template.replace("{{task_count}}", str(task_count))
            .replace("{{item_word}}", item_word)
            .replace("{{task_rows}}", task_rows)
            .replace("{{year}}", str(datetime.now().year))
        )

        subject = f"Task List: {task_count} {item_word.capitalize()} Pending"
        return subject, html_body

    def _load_template(self) -> str:
        """
        Loads the HTML template from the templates directory.

        Returns:
            str: The HTML template content.
        """
        with open(self.TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()

    def _generate_task_rows(self, tasks: List[Dict[str, Any]]) -> str:
        """
        Generates HTML rows for all tasks.

        Args:
            tasks: List of task dictionaries.

        Returns:
            str: HTML string containing all task rows.
        """
        return "\n".join(self._generate_task_row(task) for task in tasks)

    def _generate_task_row(self, task: Dict[str, Any]) -> str:
        """
        Generates an HTML row for a single task.

        Args:
            task: Task dictionary with id, titulo, fecha, and notas.

        Returns:
            str: HTML string for the task row.
        """
        date_display = self._format_date(task.get("fecha"))
        title = html.escape(task.get("titulo"))
        notes = task.get("notas", "")

        notes_html = self._generate_notes_html(notes) if notes else ""
        return f"""<tr class="task-row">
                        <td class="date-cell">
                            <span class="date-pill">{date_display}</span>
                        </td>
                        <td>
                            <span class="task-title">{title}</span>{notes_html}
                        </td>
                    </tr>"""

    def _generate_notes_html(self, notes: str) -> str:
        """
        Generates HTML for task notes, including URL detection.

        Args:
            notes: The notes text.

        Returns:
            str: HTML string for the notes section.
        """
        escaped_notes = html.escape(notes)

        # Detect URLs and convert them to links
        url_pattern = r'(https?://[^\s<>"]+|www\.[^\s<>"]+)'

        def replace_url(match):
            url = match.group(1)
            href = url if url.startswith("http") else f"https://{url}"
            return f'<a href="{href}" class="link-text">{url}</a>'

        notes_with_links = re.sub(url_pattern, replace_url, escaped_notes)

        return f"""
        <div class="task-notes">{notes_with_links}</div>"""

    def _format_date(self, date_str: Optional[str]) -> str:
        """
        Formats a date string from YYYY-MM-DD to "Mon DD" format.

        Args:
            date_str: Date in YYYY-MM-DD format, or None.

        Returns:
            str: Formatted date string like "Nov 24", or "No Date" if None.
        """
        if not date_str:
            return "No Date"

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%b %d")
        except ValueError:
            return "Invalid"
