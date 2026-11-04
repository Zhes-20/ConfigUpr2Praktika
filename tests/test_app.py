"""Тесты вывода приложения на этапе 3."""

import contextlib
import io
import os
import unittest

from src.app import main

REPOS = os.path.join(os.path.dirname(__file__), "..", "examples", "repos")


def run_app(*argv: str) -> tuple:
    """Запускает приложение и возвращает код, вывод и ошибки."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


def repo(name: str) -> str:
    """Возвращает путь к файлу из examples/repos."""
    return os.path.join(REPOS, name)


class AppTest(unittest.TestCase):
    """Запуск в тестовом режиме."""

    def test_graph_output(self) -> None:
        """Печатаются рёбра, число пакетов и цикл."""
        code, out, _ = run_app("-p", "A", "-m", "test",
                               "-s", repo("cycle.txt"))
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertIn("A -> B", lines)
        self.assertIn("C -> A, D", lines)
        self.assertIn("Packages: 4", lines)
        self.assertIn("Cycle: A -> B -> C -> A", lines)

    def test_depth_marks_leaves(self) -> None:
        """Нераскрытые из-за глубины пакеты помечаются."""
        _, out, _ = run_app("-p", "A", "-m", "test", "-d", "1",
                            "-s", repo("chain.txt"))
        self.assertIn("B -> (not expanded: max depth)", out)

    def test_unknown_package(self) -> None:
        """Пакет, которого нет в файле, даёт ошибку."""
        code, _, err = run_app("-p", "Z", "-m", "test",
                               "-s", repo("simple.txt"))
        self.assertEqual(code, 1)
        self.assertIn("not defined", err)

    def test_broken_file(self) -> None:
        """Ошибка формата файла выводится с номером строки."""
        code, _, err = run_app("-p", "A", "-m", "test",
                               "-s", repo("broken.txt"))
        self.assertEqual(code, 1)
        self.assertIn("line 3", err)


if __name__ == "__main__":
    unittest.main()
