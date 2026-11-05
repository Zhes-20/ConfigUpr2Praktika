"""Текст графа на языке Graphviz (DOT) и картинка PNG.

Картинку рисует программа dot из пакета Graphviz, текст для неё
формирует этот модуль.
"""

import os
import shutil
import subprocess
from typing import Dict

from src.graph import DependencyGraph

TIMEOUT = 120


class RenderError(Exception):
    """Картинку не удалось получить."""


def escape(text: str) -> str:
    """Экранирует обратную косую черту и кавычки по правилам DOT."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def quote(text: str) -> str:
    """Заключает текст в кавычки по правилам DOT."""
    return f'"{escape(text)}"'


def label(name: str) -> str:
    """Подпись вершины: для координат Maven версия на второй строке."""
    parts = name.split(":")
    if len(parts) != len(("group", "artifact", "version")):
        return quote(name)
    first = escape(f"{parts[0]}:{parts[1]}")
    return f'"{first}\\n{escape(parts[2])}"'


def node_style(name: str, graph: DependencyGraph,
               problems: Dict[str, str]) -> str:
    """Оформление вершины в зависимости от её состояния."""
    if name == graph.root:
        return "style=filled, fillcolor=lightblue"
    if name in problems:
        return "style=dashed, color=gray"
    if name not in graph.edges:
        return "style=dotted"
    return ""


def to_dot(graph: DependencyGraph, problems: Dict[str, str]) -> str:
    """Формирует описание графа на языке Graphviz."""
    cycle_edges = {
        (cycle[index], cycle[index + 1])
        for cycle in graph.cycles
        for index in range(len(cycle) - 1)
    }
    lines = [
        "digraph dependencies {",
        "    rankdir=LR;",
        "    node [shape=box, fontname=Helvetica];",
    ]
    for name in graph.nodes():
        style = node_style(name, graph, problems)
        attributes = f"label={label(name)}" + (f", {style}" if style else "")
        lines.append(f"    {quote(name)} [{attributes}];")
    for name, children in graph.edges.items():
        for child in children:
            color = " [color=red]" if (name, child) in cycle_edges else ""
            lines.append(f"    {quote(name)} -> {quote(child)}{color};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_png(dot_text: str, png_path: str) -> str:
    """Сохраняет текст в .dot и рисует PNG; возвращает путь к .dot."""
    dot_path = os.path.splitext(png_path)[0] + ".dot"
    with open(dot_path, "w", encoding="utf-8") as target:
        target.write(dot_text)
    program = shutil.which("dot")
    if program is None:
        raise RenderError(
            f"Graphviz is not installed: {dot_path} saved, PNG not drawn"
        )
    result = subprocess.run(
        [program, "-Tpng", "-o", png_path, dot_path],
        capture_output=True, text=True, timeout=TIMEOUT, check=False,
    )
    if result.returncode != 0:
        raise RenderError(f"dot failed: {result.stderr.strip()}")
    return dot_path
