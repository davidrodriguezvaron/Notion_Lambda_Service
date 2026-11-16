import unittest

from app.domain.task import Task
from app.infrastructure.notion.task_mapper import to_task


class TestToTask(unittest.TestCase):
    def test_maps_every_property(self):
        page = {
            "id": "abc",
            "url": "https://www.notion.so/abc",
            "properties": {
                "Tarea": {
                    "title": [
                        {"plain_text": "Pagar "},
                        {"plain_text": "ENEL"},
                        {"plain_text": " (link) "},
                    ]
                },
                "Fecha": {"date": {"start": "2026-11-21T10:30:00.000-05:00"}},
                "Notas": {
                    "rich_text": [{"plain_text": "Uno. "}, {"plain_text": "Dos."}]
                },
                "Área": {"select": {"name": "Hogar"}},
                "Recurrencia": {"select": {"name": "Mensual"}},
            },
        }
        self.assertEqual(
            to_task(page),
            Task(
                id="abc",
                url="https://www.notion.so/abc",
                title="Pagar ENEL (link)",
                due="2026-11-21T10:30:00.000-05:00",
                notes="Uno. Dos.",
                area="Hogar",
                recurrence="Mensual",
            ),
        )

    def test_missing_or_empty_properties(self):
        result = to_task(
            {
                "id": "x",
                "properties": {
                    "Tarea": {"title": []},
                    "Fecha": {"date": None},
                    "Área": {"select": None},
                },
            }
        )
        self.assertEqual(result, Task(id="x", title="", url=None))

    def test_page_without_id_fails_fast(self):
        with self.assertRaises(KeyError):
            to_task({"properties": {}})


if __name__ == "__main__":
    unittest.main()
