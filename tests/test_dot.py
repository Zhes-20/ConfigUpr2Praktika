"""Тесты текста Graphviz и рисования PNG."""

import os
import shutil
import tempfile
import unittest
import unittest.mock

from src.dot import RenderError, label, quote, render_png, to_dot
from src.graph import build_graph

PACKAGES = {"A": ["B", "C"], "B": ["A"], "C": []}


def sample_graph():
    """Граф с циклом A -> B -> A и обычным ребром A -> C."""
    return build_graph("A", lambda name: PACKAGES.get(name, []), 5)


class TextTest(unittest.TestCase):
    """Формирование текста DOT."""

    def test_structure(self) -> None:
        """Текст начинается с digraph и содержит все вершины и рёбра."""
        text = to_dot(sample_graph(), {})
        self.assertTrue(text.startswith("digraph dependencies {"))
        self.assertIn('"A" -> "C";', text)
        self.assertIn('"C" [label="C"];', text)

    def test_cycle_is_red(self) -> None:
        """Рёбра цикла выделены красным."""
        text = to_dot(sample_graph(), {})
        self.assertIn('"A" -> "B" [color=red];', text)
        self.assertIn('"B" -> "A" [color=red];', text)

    def test_root_and_problems(self) -> None:
        """Корень закрашен, незагруженный пакет пунктирный."""
        text = to_dot(sample_graph(), {"C": "not found"})
        self.assertIn("fillcolor=lightblue", text)
        self.assertIn('"C" [label="C", style=dashed, color=gray];', text)

    def test_quote_and_label(self) -> None:
        """Кавычки экранируются, версия переносится на вторую строку."""
        self.assertEqual(quote('a"b'), '"a\\"b"')
        self.assertEqual(label("g:a:1.0"), '"g:a\\n1.0"')
        self.assertEqual(label("A"), '"A"')


class RenderTest(unittest.TestCase):
    """Вызов программы dot."""

    def test_without_graphviz(self) -> None:
        """Без Graphviz файл .dot сохраняется и выводится ошибка."""
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        png = os.path.join(folder, "g.png")
        with unittest.mock.patch("shutil.which", return_value=None):
            with self.assertRaises(RenderError):
                render_png("digraph g {}", png)
        self.assertTrue(os.path.exists(os.path.join(folder, "g.dot")))

    @unittest.skipUnless(shutil.which("dot"), "Graphviz is not installed")
    def test_real_png(self) -> None:
        """С установленным Graphviz получается файл PNG."""
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        png = os.path.join(folder, "g.png")
        render_png(to_dot(sample_graph(), {}), png)
        with open(png, "rb") as image:
            self.assertEqual(image.read(len(b"\x89PNG")), b"\x89PNG")


if __name__ == "__main__":
    unittest.main()
