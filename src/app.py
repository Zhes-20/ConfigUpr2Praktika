"""Точка входа: python -m src.app --package ..."""

import sys
from typing import Dict, List, Optional, Sequence

from src.config import Config, ConfigError, load_config
from src.graph import (
    DependencyGraph,
    GraphError,
    build_graph,
    load_order,
)
from src.local_repo import LocalRepoError, load_local_repo
from src.maven import MavenSource, RepositoryError, direct_dependencies

ERRORS = (RepositoryError, LocalRepoError, GraphError)


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


def render(graph: DependencyGraph, problems: Dict[str, str]) -> List[str]:
    """Готовит текстовый вывод графа."""
    lines = []
    for name in graph.nodes():
        children = graph.edges.get(name)
        if children is None:
            lines.append(f"{name} -> (not expanded: max depth)")
        else:
            lines.append(f"{name} -> {', '.join(children) or '(none)'}")
    lines.append(f"Packages: {len(graph.nodes())}")
    for cycle in graph.cycles:
        lines.append("Cycle: " + " -> ".join(cycle))
    for name, reason in problems.items():
        lines.append(f"Not loaded: {name}: {reason}")
    return lines


def render_order(graph: DependencyGraph) -> List[str]:
    """Готовит нумерованный порядок загрузки."""
    lines = ["Load order (dependencies first):"]
    in_cycle = {name for cycle in graph.cycles for name in cycle}
    for number, name in enumerate(load_order(graph), start=1):
        mark = " (cycle)" if name in in_cycle else ""
        lines.append(f"{number:4}. {name}{mark}")
    return lines


def run(config: Config) -> List[str]:
    """Строит граф в выбранном режиме и возвращает строки вывода."""
    if config.mode == "test":
        graph, problems = graph_from_test_repo(config), {}
    else:
        graph, problems = graph_from_maven(config)
    title = (f"Dependency graph of {config.package} "
             f"(max depth {config.depth}, exclude: {config.exclude or '-'})")
    if config.load_order:
        return [title] + render_order(graph)
    return [title] + render(graph, problems)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Строит и выводит граф зависимостей или сообщает об ошибке."""
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
