"""Тесты обхода графа и тестового репозитория."""

import os
import tempfile
import unittest

from src.graph import GraphError, build_graph, find_cycles, load_order
from src.local_repo import LocalRepoError, load_local_repo, parse_local_repo

REPOS = os.path.join(os.path.dirname(__file__), "..", "examples", "repos")
DEEP = 10


def graph_of(name: str, root: str = "A", depth: int = DEEP,
             exclude: str = ""):
    """Строит граф по файлу из examples/repos."""
    packages = load_local_repo(os.path.join(REPOS, name))
    return build_graph(root, lambda item: packages.get(item, []),
                       depth, exclude)


class LocalRepoTest(unittest.TestCase):
    """Разбор файла тестового репозитория."""

    def test_parse(self) -> None:
        """Строки со стрелкой разбираются, комментарии пропускаются."""
        packages = parse_local_repo("# x\n\nA -> B, C\nB ->\n")
        self.assertEqual(packages, {"A": ["B", "C"], "B": []})

    def assert_bad(self, text: str, message: str) -> None:
        """Проверяет, что текст отклонён с сообщением."""
        with self.assertRaises(LocalRepoError) as caught:
            parse_local_repo(text)
        self.assertIn(message, str(caught.exception))

    def test_errors(self) -> None:
        """Ошибки формата указывают номер строки."""
        self.assert_bad("A -> B\nB C\n", "line 2")
        self.assert_bad("A -> b\n", "capital")
        self.assert_bad("A ->\nA -> B\n", "twice")
        self.assert_bad("# only comment\n", "no packages")

    def test_missing_file(self) -> None:
        """Отсутствующий файл даёт ошибку чтения."""
        with self.assertRaises(LocalRepoError):
            load_local_repo(os.path.join(tempfile.gettempdir(), "nope.txt"))


class TraversalTest(unittest.TestCase):
    """Обход в глубину по разным графам."""

    def test_simple(self) -> None:
        """Прямые зависимости попадают в граф в исходном порядке."""
        graph = graph_of("simple.txt")
        self.assertEqual(graph.nodes(), ["A", "B", "C"])
        self.assertEqual(graph.edges["A"], ["B", "C"])

    def test_diamond(self) -> None:
        """Общая зависимость встречается в графе один раз."""
        graph = graph_of("diamond.txt")
        self.assertEqual(graph.nodes(), ["A", "B", "D", "C"])
        self.assertEqual(graph.cycles, [])

    def test_depth_limit(self) -> None:
        """Пакеты на предельной глубине не раскрываются."""
        graph = graph_of("chain.txt", depth=2)
        self.assertEqual(graph.nodes(), ["A", "B", "C"])
        self.assertNotIn("C", graph.edges)

    def test_shorter_path_wins(self) -> None:
        """Пакет, найденный сначала глубоко, раскрывается по короткому пути."""
        packages = {"A": ["B", "C"], "B": ["C"], "C": ["D"], "D": []}
        graph = build_graph("A", packages.get, 2)
        self.assertEqual(graph.depth["C"], 1)
        self.assertEqual(graph.edges["C"], ["D"])

    def test_exclude(self) -> None:
        """Пакет с подстрокой отбрасывается вместе со своей веткой."""
        graph = graph_of("exclude.txt", exclude="TEST")
        self.assertEqual(graph.nodes(), ["A", "B", "C"])

    def test_exclude_root(self) -> None:
        """Исключить сам анализируемый пакет нельзя."""
        with self.assertRaises(GraphError):
            graph_of("exclude.txt", root="TESTKIT", exclude="TEST")

    def test_undefined_dependency(self) -> None:
        """Неописанная зависимость становится листом."""
        graph = graph_of("undefined.txt")
        self.assertEqual(graph.edges["X"], [])

    def test_cycle(self) -> None:
        """Цикл найден, обход завершился."""
        graph = graph_of("cycle.txt")
        self.assertEqual(graph.cycles, [["A", "B", "C", "A"]])
        self.assertEqual(graph.nodes(), ["A", "B", "C", "D"])

    def test_self_loop(self) -> None:
        """Зависимость от самого себя - цикл из одного пакета."""
        graph = graph_of("self.txt")
        self.assertEqual(graph.cycles, [["A", "A"]])

    def test_cycle_beyond_depth(self) -> None:
        """Цикл за пределом глубины не виден."""
        graph = graph_of("cycle.txt", depth=2)
        self.assertEqual(graph.cycles, [])

    def test_long_chain_without_recursion(self) -> None:
        """Длинная цепочка обходится без переполнения стека вызовов."""
        size = 5000
        names = [f"N{index}" for index in range(size)]
        links = {name: [nxt] for name, nxt in zip(names, names[1:])}
        graph = build_graph(names[0], lambda item: links.get(item, []), size)
        self.assertEqual(len(graph.nodes()), size)
        self.assertEqual(find_cycles(graph.edges, names[0]), [])


class LoadOrderTest(unittest.TestCase):
    """Порядок загрузки зависимостей."""

    def assert_before(self, order: list, first: str, second: str) -> None:
        """Проверяет, что first стоит в списке раньше second."""
        self.assertLess(order.index(first), order.index(second))

    def test_diamond(self) -> None:
        """Каждый пакет идёт после своих зависимостей, без повторов."""
        order = load_order(graph_of("diamond.txt"))
        self.assertEqual(order, ["D", "B", "C", "A"])

    def test_chain(self) -> None:
        """Цепочка загружается с конца."""
        self.assertEqual(load_order(graph_of("chain.txt")),
                         ["F", "E", "D", "C", "B", "A"])

    def test_depth_and_exclude(self) -> None:
        """Ограничения графа действуют и на порядок."""
        self.assertEqual(load_order(graph_of("chain.txt", depth=2)),
                         ["C", "B", "A"])
        order = load_order(graph_of("exclude.txt", exclude="TEST"))
        self.assertEqual(order, ["C", "B", "A"])

    def test_cycle(self) -> None:
        """При цикле обход завершается, каждый пакет назван один раз."""
        order = load_order(graph_of("cycle.txt"))
        self.assertEqual(sorted(order), ["A", "B", "C", "D"])
        self.assert_before(order, "D", "C")
        self.assertEqual(order[-1], "A")

    def test_root_is_last(self) -> None:
        """Анализируемый пакет загружается последним."""
        for name in ("simple.txt", "self.txt", "undefined.txt"):
            self.assertEqual(load_order(graph_of(name))[-1], "A")


if __name__ == "__main__":
    unittest.main()
