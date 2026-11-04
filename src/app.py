"""Точка входа: python -m src.app --package ..."""

import sys
from typing import Optional, Sequence

from src.config import ConfigError, load_config


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Выводит настройки в формате ключ-значение или сообщает об ошибке."""
    try:
        config = load_config(argv)
    except ConfigError as error:
        print(f"config error: {error}", file=sys.stderr)
        return 1
    for key, value in config.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
