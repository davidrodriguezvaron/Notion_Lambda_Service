import unittest

from app.presentation.email.linkify import notes_to_html


def linkify(text):
    return notes_to_html(text, "#a0522d", "accent")


class TestNotesToHtml(unittest.TestCase):
    def test_links_urls_and_escapes_query_strings(self):
        result = linkify("Ver https://example.com/a?b=1&c=2.")
        self.assertIn('href="https://example.com/a?b=1&amp;c=2"', result)
        self.assertTrue(result.endswith(">https://example.com/a?b=1&amp;c=2</a>."))

    def test_www_links_get_https(self):
        self.assertIn('href="https://www.test.co"', linkify("www.test.co"))

    def test_escapes_html_and_keeps_line_breaks(self):
        self.assertEqual(linkify("<b>uno</b>\ndos"), "&lt;b&gt;uno&lt;/b&gt;<br>dos")

    def test_link_style(self):
        self.assertIn('class="accent" style="color:#a0522d;', linkify("http://a.co"))


if __name__ == "__main__":
    unittest.main()
