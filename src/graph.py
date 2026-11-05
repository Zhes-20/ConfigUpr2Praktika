"""Граф зависимостей: обход в глубину без рекурсии.

Обход идёт по явному стеку. Пакет раскрывается, если до него добрались
не глубже max_depth; пакеты с подстрокой exclude пропускаются. Если до
пакета позже нашёлся более короткий путь, он раскрывается заново, чтобы
ограничение глубины считалось от кратчайшего пути.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

Children = Callable[[str], List[str]]


class GraphError(Exception):
    """Граф нельзя построить с заданными параметрами."""


@dataclass
class DependencyGraph:
    """Результат обхода."""

    root: str
    edges: Dict[str, List[str]] = field(default_factory=dict)
    depth: Dict[str, int] = field(default_factory=dict)
    cycles: List[List[str]] = field(default_factory=list)

    def nodes(self) -> List[str]:
        """Возвращает все пакеты графа в порядке обнаружения."""
        found = list(self.depth)
        for children in self.edges.values():
            found.extend(child for child in children if child not in found)
        return found


def is_excluded(name: str, exclude: str) -> bool:
    """Сообщает, содержит ли имя пакета исключаемую подстроку."""
    return bool(exclude) and exclude in name


def build_graph(root: str, children_of: Children, max_depth: int,
                exclude: str = "") -> DependencyGraph:
    """Строит граф транзитивных зависимостей пакета root."""
    if is_excluded(root, exclude):
        raise GraphError(f"package {root} itself matches exclude '{exclude}'")
    graph = DependencyGraph(root=root)
    stack: List[Tuple[str, int]] = [(root, 0)]
    while stack:
        name, level = stack.pop()
        if graph.depth.get(name, level + 1) <= level:
            continue
        graph.depth[name] = level
        if level >= max_depth:
            graph.edges.pop(name, None)
            continue
        kept = [child for child in children_of(name)
                if not is_excluded(child, exclude)]
        graph.edges[name] = kept
        stack.extend((child, level + 1) for child in reversed(kept))
    graph.cycles = find_cycles(graph.edges, root)
    return graph


def find_cycles(edges: Dict[str, List[str]], root: str) -> List[List[str]]:
    """Находит циклы без рекурсии: ребро в пакет из текущего пути."""
    cycles: List[List[str]] = []
    finished = set()
    path: List[str] = [root]
    stack = [iter(edges.get(root, []))]
    while stack:
        child = next(stack[-1], None)
        if child is None:
            finished.add(path.pop())
            stack.pop()
        elif child in path:
            cycles.append(path[path.index(child):] + [child])
        elif child not in finished:
            path.append(child)
            stack.append(iter(edges.get(child, [])))
    return cycles

