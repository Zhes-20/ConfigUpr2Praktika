"""Настройки приложения, получаемые из опций командной строки."""

import argparse
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple
from urllib.parse import urlparse

MAVEN_CENTRAL = "https://repo1.maven.org/maven2"
MODES = ("remote", "test")
DEFAULT_IMAGE = "graph.png"
DEFAULT_DEPTH = 5
COORDINATES = re.compile(r"[\w.\-]+:[\w.\-]+:[\w.\-]+")
TEST_NAME = re.compile(r"[A-Z]+")


class ConfigError(Exception):
    """Неверное значение одной из опций."""


@dataclass(frozen=True)
class Config:
    """Все параметры, которые может задать пользователь."""

    package: str
    source: str
    mode: str
    image: str
    depth: int
    exclude: str
    load_order: bool = False

    def items(self) -> List[Tuple[str, str]]:
        """Возвращает параметры парами ключ-значение."""
        return [
            ("package", self.package),
            ("source", self.source),
            ("mode", self.mode),
            ("image", self.image),
            ("depth", str(self.depth)),
            ("exclude", self.exclude),
            ("load_order", str(self.load_order).lower()),
        ]


def make_parser() -> argparse.ArgumentParser:
    """Описывает опции командной строки."""
    parser = argparse.ArgumentParser(
        prog="depviz",
        description="Граф зависимостей пакетов Maven",
    )
    parser.add_argument(
        "-p", "--package", required=True,
        help="пакет groupId:artifactId:version, в режиме test - буквы A-Z",
    )
    parser.add_argument(
        "-s", "--source", default=MAVEN_CENTRAL,
        help="URL репозитория или путь к файлу тестового репозитория",
    )
    parser.add_argument(
        "-m", "--mode", default="remote",
        help="режим работы: remote или test (тестовый репозиторий)",
    )
    parser.add_argument(
        "-o", "--image", default=DEFAULT_IMAGE,
        help="имя PNG-файла с изображением графа",
    )
    parser.add_argument(
        "-d", "--depth", default=str(DEFAULT_DEPTH),
        help="максимальная глубина анализа зависимостей",
    )
    parser.add_argument(
        "-e", "--exclude", default="",
        help="не учитывать пакеты, имя которых содержит подстроку",
    )
    parser.add_argument(
        "-l", "--load-order", action="store_true",
        help="вывести порядок загрузки зависимостей",
    )
    return parser


def check_mode(mode: str) -> str:
    """Проверяет режим работы."""
    if mode not in MODES:
        raise ConfigError(f"mode: expected remote or test, got '{mode}'")
    return mode


def check_package(package: str, mode: str) -> str:
    """Проверяет имя пакета для выбранного режима."""
    if mode == "test" and not TEST_NAME.fullmatch(package):
        raise ConfigError(
            f"package: '{package}' must be capital latin letters in test mode"
        )
    if mode == "remote" and not COORDINATES.fullmatch(package):
        raise ConfigError(
            f"package: '{package}' must look like groupId:artifactId:version"
        )
    return package


def check_source(source: str, mode: str) -> str:
    """Проверяет адрес репозитория или путь к тестовому файлу."""
    if mode == "test":
        if not os.path.isfile(source):
            raise ConfigError(f"source: test repository not found: {source}")
        return source
    address = urlparse(source)
    if address.scheme not in ("http", "https") or not address.netloc:
        raise ConfigError(f"source: '{source}' is not an http(s) URL")
    return source.rstrip("/")


def check_image(image: str) -> str:
    """Проверяет имя файла изображения."""
    name = os.path.basename(image)
    if not name.lower().endswith(".png") or name.lower() == ".png":
        raise ConfigError(f"image: '{image}' must be a .png file name")
    folder = os.path.dirname(image)
    if folder and not os.path.isdir(folder):
        raise ConfigError(f"image: folder does not exist: {folder}")
    return image


def check_depth(depth: str) -> int:
    """Проверяет глубину: целое число не меньше единицы."""
    try:
        value = int(depth)
    except ValueError as error:
        raise ConfigError(f"depth: '{depth}' is not an integer") from error
    if value < 1:
        raise ConfigError(f"depth: must be at least 1, got {value}")
    return value


def check_exclude(exclude: str) -> str:
    """Проверяет подстроку фильтра."""
    if any(symbol.isspace() for symbol in exclude):
        raise ConfigError("exclude: substring must not contain spaces")
    return exclude


def load_config(argv: Optional[Sequence[str]] = None) -> Config:
    """Читает опции и возвращает проверенные настройки."""
    args = make_parser().parse_args(argv)
    mode = check_mode(args.mode)
    return Config(
        package=check_package(args.package, mode),
        source=check_source(args.source, mode),
        mode=mode,
        image=check_image(args.image),
        depth=check_depth(args.depth),
        exclude=check_exclude(args.exclude),
        load_order=args.load_order,
    )
