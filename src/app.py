"""Точка входа: python -m src.app --package ..."""

import sys
from typing import List, Optional, Sequence

from src.config import Config, ConfigError, load_config
from src.dot import RenderError, render_png, to_dot
from src.graph import DependencyGraph, GraphError, build_graph
from src.local_repo import LocalRepoError, load_local_repo
from src.maven import MavenSource, RepositoryError, direct_dependencies

ERRORS = (RepositoryError, LocalRepoError, GraphError, RenderError, OSError)


def graph_from_test_repo(config: Config) -> DependencyGraph:
    """Строит граф по файлу тестового репозитория."""
    packages = load_local_repo(config.source)
    if config.package not in packages:
        raise LocalRepoError(f"package {config.package} is not defined")
    return build_graph(config.package, lambda name: packages.get(name, []),
                       config.depth, config.exclude)


def graph_from_maven(config: Config) -> tuple:
    """Строит граф по Maven-репозиторию; возвращает граф и проблемы."""
    direct_dependencies(config.source, config.package)
    source = MavenSource(config.source)
    graph = build_graph(config.package, source.children,
                        config.depth, config.exclude)
    return graph, source.problems


def run(config: Config) -> List[str]:
    """Строит граф, печатает его на языке Graphviz и рисует PNG."""
    if config.mode == "test":
        graph, problems = graph_from_test_repo(config), {}
    else:
        graph, problems = graph_from_maven(config)
    dot_text = to_dot(graph, problems)
    lines = [dot_text.rstrip("\n")]
    lines.extend(f"cycle: {' -> '.join(cycle)}" for cycle in graph.cycles)
    lines.extend(f"not loaded: {name}: {reason}"
                 for name, reason in problems.items())
    dot_path = render_png(dot_text, config.image)
    lines.append(f"saved: {dot_path}")
    lines.append(f"saved: {config.image}")
    return lines


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Строит и рисует граф зависимостей или сообщает об ошибке."""
    try:
        config = load_config(argv)
    except ConfigError as error:
        print(f"config error: {error}", file=sys.stderr)
        return 1
    try:
        lines = run(config)
    except ERRORS as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
