"""Тестовый репозиторий: граф пакетов, описанный текстовым файлом.

Формат строки: ``A -> B, C`` - пакет A зависит от B и C.
Пакет без зависимостей: ``D ->``. Имена - большие латинские буквы.
Пустые строки и строки, начинающиеся с ``#``, пропускаются.
"""

import re
from typing import Dict, List

NAME = re.compile(r"[A-Z]+")


class LocalRepoError(Exception):
    """Ошибка в файле тестового репозитория."""


def parse_line(line: str, number: int) -> tuple:
    """Разбирает строку вида A -> B, C."""
    if "->" not in line:
        raise LocalRepoError(f"line {number}: expected 'NAME -> DEPS'")
    left, right = line.split("->", 1)
    name = left.strip()
    deps = [item.strip() for item in right.split(",") if item.strip()]
    for item in [name] + deps:
        if not NAME.fullmatch(item):
            raise LocalRepoError(
                f"line {number}: '{item}' is not capital latin letters"
            )
    return name, deps


def parse_local_repo(text: str) -> Dict[str, List[str]]:
    """Строит словарь пакет -> прямые зависимости."""
    packages: Dict[str, List[str]] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, deps = parse_line(line, number)
        if name in packages:
            raise LocalRepoError(f"line {number}: {name} is defined twice")
        packages[name] = deps
    if not packages:
        raise LocalRepoError("no packages in test repository")
    return packages


def load_local_repo(path: str) -> Dict[str, List[str]]:
    """Читает файл тестового репозитория."""
    try:
        with open(path, encoding="utf-8") as source:
            return parse_local_repo(source.read())
    except (OSError, UnicodeDecodeError) as error:
        raise LocalRepoError(f"cannot read {path}: {error}") from error
