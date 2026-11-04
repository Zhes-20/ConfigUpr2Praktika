"""Тесты чтения и проверки опций командной строки."""

import contextlib
import io
import os
import tempfile
import unittest

from src.app import main
from src.config import (
    DEFAULT_DEPTH,
    DEFAULT_IMAGE,
    MAVEN_CENTRAL,
    ConfigError,
    load_config,
)

PACKAGE = "junit:junit:4.13.2"


def run_app(*argv: str) -> tuple:
    """Запускает приложение и возвращает код, вывод и текст ошибки."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class DefaultsTest(unittest.TestCase):
    """Значения по умолчанию и разбор всех опций."""

    def test_only_package(self) -> None:
        """Без остальных опций берутся значения по умолчанию."""
        config = load_config(["--package", PACKAGE])
        self.assertEqual(config.source, MAVEN_CENTRAL)
        self.assertEqual(config.mode, "remote")
        self.assertEqual(config.image, DEFAULT_IMAGE)
        self.assertEqual(config.depth, DEFAULT_DEPTH)
        self.assertEqual(config.exclude, "")

    def test_short_options(self) -> None:
        """Короткие имена опций дают тот же результат."""
        config = load_config([
            "-p", PACKAGE, "-s", "https://example.org/maven2/",
            "-o", "out.png", "-d", "3", "-e", "test",
        ])
        self.assertEqual(config.source, "https://example.org/maven2")
        self.assertEqual(config.image, "out.png")
        self.assertEqual(config.depth, 3)
        self.assertEqual(config.exclude, "test")

    def test_test_mode(self) -> None:
        """В тестовом режиме источник - существующий файл."""
        with tempfile.NamedTemporaryFile(suffix=".txt") as repo:
            config = load_config(
                ["-p", "ABC", "-m", "test", "-s", repo.name]
            )
        self.assertEqual(config.mode, "test")
        self.assertEqual(config.package, "ABC")


class ErrorsTest(unittest.TestCase):
    """Каждая опция с неверным значением отклоняется."""

    def assert_error(self, argv: list, text: str) -> None:
        """Проверяет, что опции отклонены с сообщением про text."""
        with self.assertRaises(ConfigError) as caught:
            load_config(argv)
        self.assertIn(text, str(caught.exception))

    def test_package(self) -> None:
        """Пакет должен быть в формате координат Maven."""
        self.assert_error(["-p", "junit"], "groupId:artifactId:version")
        self.assert_error(["-p", "a:b"], "groupId:artifactId:version")

    def test_package_in_test_mode(self) -> None:
        """В тестовом режиме пакет - большие латинские буквы."""
        with tempfile.NamedTemporaryFile() as repo:
            self.assert_error(
                ["-p", "abc", "-m", "test", "-s", repo.name], "capital"
            )

    def test_mode(self) -> None:
        """Неизвестный режим отклоняется."""
        self.assert_error(["-p", PACKAGE, "-m", "local"], "mode")

    def test_source(self) -> None:
        """Источник - URL или существующий файл."""
        self.assert_error(["-p", PACKAGE, "-s", "repo1.maven.org"], "URL")
        self.assert_error(["-p", PACKAGE, "-s", "ftp://host/x"], "URL")
        self.assert_error(
            ["-p", "A", "-m", "test", "-s", "missing.txt"], "not found"
        )

    def test_image(self) -> None:
        """Изображение - PNG-файл в существующей папке."""
        self.assert_error(["-p", PACKAGE, "-o", "graph.svg"], ".png")
        self.assert_error(["-p", PACKAGE, "-o", ".png"], ".png")
        missing = os.path.join("no_such_dir", "g.png")
        self.assert_error(["-p", PACKAGE, "-o", missing], "folder")

    def test_depth(self) -> None:
        """Глубина - целое число от единицы."""
        self.assert_error(["-p", PACKAGE, "-d", "two"], "integer")
        self.assert_error(["-p", PACKAGE, "-d", "0"], "at least 1")
        self.assert_error(["-p", PACKAGE, "--depth=-3"], "at least 1")

    def test_exclude(self) -> None:
        """Подстрока фильтра без пробелов."""
        self.assert_error(["-p", PACKAGE, "-e", "a b"], "spaces")


class OutputTest(unittest.TestCase):
    """Сообщения об ошибках при запуске."""

    def test_error_output(self) -> None:
        """Ошибка печатается в поток ошибок, код возврата не ноль."""
        code, out, err = run_app("-p", PACKAGE, "-d", "0")
        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("config error: depth", err)


if __name__ == "__main__":
    unittest.main()
