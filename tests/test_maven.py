"""Тесты получения прямых зависимостей из pom.xml."""

import contextlib
import io
import pathlib
import shutil
import tempfile
import unittest
import unittest.mock

from src.app import main
from src.maven import (
    RepositoryError,
    direct_dependencies,
    parse_pom,
    pom_url,
    substitute,
)

NS = 'xmlns="http://maven.apache.org/POM/4.0.0"'

PARENT_POM = f"""<project {NS}>
  <groupId>org.demo</groupId>
  <artifactId>parent</artifactId>
  <version>1.0</version>
  <properties><lib.version>2.5</lib.version></properties>
  <dependencyManagement><dependencies>
    <dependency>
      <groupId>org.lib</groupId><artifactId>managed</artifactId>
      <version>${{lib.version}}</version>
    </dependency>
  </dependencies></dependencyManagement>
</project>"""

APP_POM = f"""<project {NS}>
  <parent>
    <groupId>org.demo</groupId><artifactId>parent</artifactId>
    <version>1.0</version>
  </parent>
  <artifactId>app</artifactId>
  <properties><own>3.1</own></properties>
  <dependencies>
    <dependency>
      <groupId>org.lib</groupId><artifactId>plain</artifactId>
      <version>${{own}}</version>
    </dependency>
    <dependency>
      <groupId>org.lib</groupId><artifactId>managed</artifactId>
    </dependency>
    <dependency>
      <groupId>${{project.groupId}}</groupId><artifactId>core</artifactId>
      <version>${{project.version}}</version><scope>runtime</scope>
    </dependency>
    <dependency>
      <groupId>org.lib</groupId><artifactId>extra</artifactId>
      <version>1</version><scope>test</scope><optional>true</optional>
    </dependency>
  </dependencies>
  <build><plugins><plugin>
    <artifactId>not-a-dependency</artifactId><version>9</version>
  </plugin></plugins></build>
</project>"""


class FakeRepository:
    """Временная папка в формате Maven-репозитория."""

    def __init__(self) -> None:
        """Создаёт папку с двумя pom.xml."""
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.base = self.folder.as_uri()
        self.add("org.demo:parent:1.0", PARENT_POM)
        self.add("org.demo:app:1.0", APP_POM)

    def add(self, coordinates: str, text: str) -> None:
        """Кладёт pom.xml по пути, который строит pom_url."""
        relative = pom_url("", coordinates).lstrip("/")
        target = self.folder / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def remove(self) -> None:
        """Удаляет временную папку."""
        shutil.rmtree(self.folder)


class PomTest(unittest.TestCase):
    """Разбор одного pom.xml."""

    def test_url(self) -> None:
        """Адрес строится по правилам Maven-репозитория."""
        self.assertEqual(
            pom_url("https://repo", "org.slf4j:slf4j-api:2.0.9"),
            "https://repo/org/slf4j/slf4j-api/2.0.9/slf4j-api-2.0.9.pom",
        )

    def test_parse(self) -> None:
        """Читаются родитель, свойства и только раздел dependencies."""
        pom = parse_pom(APP_POM.encode())
        self.assertEqual(pom.group, "org.demo")
        self.assertEqual(pom.parent, "org.demo:parent:1.0")
        self.assertEqual(pom.properties, {"own": "3.1"})
        artifacts = [item["artifactId"] for item in pom.dependencies]
        self.assertEqual(artifacts, ["plain", "managed", "core", "extra"])

    def test_bad_xml(self) -> None:
        """Повреждённый pom.xml даёт понятную ошибку."""
        with self.assertRaises(RepositoryError):
            parse_pom(b"<project><broken></project>")

    def test_substitute(self) -> None:
        """Свойства подставляются, в том числе вложенные."""
        values = {"a": "${b}", "b": "7"}
        self.assertEqual(substitute("v${a}-${x}", values), "v7-${x}")


class DependenciesTest(unittest.TestCase):
    """Прямые зависимости с учётом родительского pom.xml."""

    def test_versions_are_resolved(self) -> None:
        """Версии берутся из свойств, родителя и самого проекта."""
        repo = FakeRepository()
        try:
            found = direct_dependencies(repo.base, "org.demo:app:1.0")
        finally:
            repo.remove()
        self.assertEqual([item.coordinates() for item in found], [
            "org.lib:plain:3.1",
            "org.lib:managed:2.5",
            "org.demo:core:1.0",
            "org.lib:extra:1",
        ])
        self.assertEqual(found[2].scope, "runtime")
        self.assertTrue(found[3].optional)

    def test_missing_package(self) -> None:
        """Отсутствующий пакет даёт ошибку с адресом файла."""
        repo = FakeRepository()
        try:
            with self.assertRaises(RepositoryError) as caught:
                direct_dependencies(repo.base, "org.demo:none:1.0")
        finally:
            repo.remove()
        self.assertIn("none-1.0.pom", str(caught.exception))

    def test_bom_import(self) -> None:
        """Версия из BOM, подключённого через scope import, находится."""
        repo = FakeRepository()
        repo.add("org.demo:bom:1.0", f"""<project {NS}>
  <groupId>org.demo</groupId><artifactId>bom</artifactId>
  <version>1.0</version>
  <dependencyManagement><dependencies><dependency>
    <groupId>org.lib</groupId><artifactId>from-bom</artifactId>
    <version>${{project.version}}.4</version>
  </dependency></dependencies></dependencyManagement>
</project>""")
        repo.add("org.demo:user:1.0", f"""<project {NS}>
  <groupId>org.demo</groupId><artifactId>user</artifactId>
  <version>1.0</version>
  <dependencyManagement><dependencies><dependency>
    <groupId>org.demo</groupId><artifactId>bom</artifactId>
    <version>1.0</version><type>pom</type><scope>import</scope>
  </dependency></dependencies></dependencyManagement>
  <dependencies><dependency>
    <groupId>org.lib</groupId><artifactId>from-bom</artifactId>
  </dependency></dependencies>
</project>""")
        try:
            found = direct_dependencies(repo.base, "org.demo:user:1.0")
        finally:
            repo.remove()
        self.assertEqual(found[0].coordinates(), "org.lib:from-bom:1.0.4")


class AppTest(unittest.TestCase):
    """Вывод приложения на этапе 2."""

    def run_app(self, *argv: str) -> tuple:
        """Запускает приложение и возвращает код, вывод и ошибки."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_prints_dependencies(self) -> None:
        """Печатаются координаты, область и признак optional."""
        repo = FakeRepository()
        try:
            with unittest.mock.patch(
                "src.config.MAVEN_CENTRAL", repo.base
            ), unittest.mock.patch(
                "src.config.urlparse",
                return_value=unittest.mock.Mock(scheme="https", netloc="x"),
            ):
                code, out, _ = self.run_app("-p", "org.demo:app:1.0",
                                            "-s", repo.base)
        finally:
            repo.remove()
        self.assertEqual(code, 0)
        self.assertIn("  org.lib:managed:2.5 (compile)", out)
        self.assertIn("  org.lib:extra:1 (test, optional)", out)

    def test_test_mode_is_not_ready(self) -> None:
        """Тестовый режим на этом этапе сообщает об ошибке."""
        with tempfile.NamedTemporaryFile() as repo_file:
            code, _, err = self.run_app("-p", "A", "-m", "test",
                                        "-s", repo_file.name)
        self.assertEqual(code, 1)
        self.assertIn("repository error", err)


if __name__ == "__main__":
    unittest.main()
