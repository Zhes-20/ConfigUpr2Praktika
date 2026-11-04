"""Точка входа: python -m src.app --package ..."""

import sys
from typing import Optional, Sequence

from src.config import Config, ConfigError, load_config
from src.maven import RepositoryError, direct_dependencies


def describe(config: Config) -> list:
    """Возвращает строки с прямыми зависимостями пакета."""
    if config.mode == "test":
        raise RepositoryError("test mode is not supported yet")
    lines = []
    for item in direct_dependencies(config.source, config.package):
        mark = ", optional" if item.optional else ""
        lines.append(f"{item.coordinates()} ({item.scope}{mark})")
    return lines or [f"{config.package} has no dependencies"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Выводит прямые зависимости пакета или сообщает об ошибке."""
    try:
        config = load_config(argv)
    except ConfigError as error:
        print(f"config error: {error}", file=sys.stderr)
        return 1
    try:
        lines = describe(config)
    except RepositoryError as error:
        print(f"repository error: {error}", file=sys.stderr)
        return 1
    print(f"Direct dependencies of {config.package}:")
    for line in lines:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
