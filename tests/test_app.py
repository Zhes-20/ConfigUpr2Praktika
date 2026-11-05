"""Тесты работы приложения на этапе 5."""

import contextlib
import io
import os
import shutil
import tempfile
import unittest
import unittest.mock

from src.app import main

REPOS = os.path.join(os.path.dirname(__file__), "..", "examples", "repos")


def repo(name: str) -> str:
    """Возвращает путь к файлу из examples/repos."""
    return os.path.join(REPOS, name)


class AppTest(unittest.TestCase):
    """Запуск в тестовом режиме с подменой программы dot."""

    def setup_folder(self) -> str:
        """Создаёт временную папку и регистрирует её удаление."""
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        return folder

    def run_app(self, *argv: str) -> tuple:
        """Запускает приложение, картинку не рисует."""
        image = os.path.join(self.setup_folder(), "g.png")
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch("src.app.render_png",
                                 return_value=image[:-3] + "dot"), \
                contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            code = main(list(argv) + ["-o", image])
        return code, out.getvalue(), err.getvalue()

    def test_dot_output(self) -> None:
        """Печатается текст DOT, цикл и сохранённые файлы."""
        code, out, _ = self.run_app("-p", "A", "-m", "test",
                                    "-s", repo("cycle.txt"))
        self.assertEqual(code, 0)
        self.assertIn("digraph dependencies {", out)
        self.assertIn('"C" -> "A" [color=red];', out)
        self.assertIn("cycle: A -> B -> C -> A", out)
        self.assertIn("saved: ", out)

    def test_unknown_package(self) -> None:
        """Пакет, которого нет в файле, даёт ошибку."""
        code, _, err = self.run_app("-p", "Z", "-m", "test",
                                    "-s", repo("simple.txt"))
        self.assertEqual(code, 1)
        self.assertIn("not defined", err)

    def test_broken_file(self) -> None:
        """Ошибка формата файла выводится с номером строки."""
        code, _, err = self.run_app("-p", "A", "-m", "test",
                                    "-s", repo("broken.txt"))
        self.assertEqual(code, 1)
        self.assertIn("line 3", err)


if __name__ == "__main__":
    unittest.main()
