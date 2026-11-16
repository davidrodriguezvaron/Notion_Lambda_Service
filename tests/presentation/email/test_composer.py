import unittest
from unittest.mock import Mock

from app.presentation.email.composer import DigestEmailComposer
from tests.fakes import task
from tests.presentation.email.helpers import agenda


class TestDigestEmailComposer(unittest.TestCase):
    def test_combines_subject_and_both_bodies(self):
        html_renderer, text_renderer = Mock(), Mock()
        html_renderer.render.return_value = "<html>"
        text_renderer.render.return_value = "texto"
        a = agenda(task("c", "2026-11-16"))

        message = DigestEmailComposer(html_renderer, text_renderer).compose(
            a, ["moved"], ["warn"]
        )

        self.assertEqual(message.subject, "Tareas: 1 hoy")
        self.assertEqual((message.html, message.text), ("<html>", "texto"))
        html_renderer.render.assert_called_once_with(a, ["moved"], ["warn"])
        text_renderer.render.assert_called_once_with(a, ["moved"], ["warn"])


if __name__ == "__main__":
    unittest.main()
