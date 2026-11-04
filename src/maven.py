"""Получение прямых зависимостей пакета из Maven-репозитория.

Файл pom.xml скачивается по URL и разбирается стандартным модулем
xml.etree. Версии в виде ${свойство} и версии из dependencyManagement
берутся из самого pom.xml, из цепочки его родительских pom.xml и из
подключённых через scope import файлов BOM.
"""

import functools
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from typing import Dict, List, Optional

TIMEOUT = 60
MAX_PARENTS = 20
PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")
TRANSITIVE_SCOPES = ("compile", "runtime")


class RepositoryError(Exception):
    """Пакет не найден или его описание нельзя прочитать."""


@dataclass(frozen=True)
class Dependency:
    """Одна прямая зависимость из раздела dependencies."""

    group: str
    artifact: str
    version: str
    scope: str = "compile"
    optional: bool = False

    def coordinates(self) -> str:
        """Возвращает строку groupId:artifactId:version."""
        return f"{self.group}:{self.artifact}:{self.version}"


@dataclass
class Pom:
    """Нужные для анализа части одного pom.xml."""

    group: str
    artifact: str
    version: str
    parent: Optional[str] = None
    properties: Dict[str, str] = field(default_factory=dict)
    managed: Dict[str, str] = field(default_factory=dict)
    dependencies: List[Dict[str, str]] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)


def pom_url(base: str, coordinates: str) -> str:
    """Строит адрес pom.xml по координатам пакета."""
    group, artifact, version = coordinates.split(":")
    path = group.replace(".", "/")
    return f"{base}/{path}/{artifact}/{version}/{artifact}-{version}.pom"


@functools.lru_cache(maxsize=None)
def download(url: str) -> bytes:
    """Скачивает файл по адресу."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise RepositoryError(f"not found in repository: {url}") from error
    except (urllib.error.URLError, OSError) as error:
        raise RepositoryError(f"cannot download {url}: {error}") from error


def strip_namespaces(root: ElementTree.Element) -> None:
    """Убирает пространство имён из тегов, чтобы искать по коротким."""
    for element in root.iter():
        element.tag = element.tag.split("}")[-1]


def text_of(element: Optional[ElementTree.Element], tag: str) -> str:
    """Возвращает текст вложенного тега или пустую строку."""
    if element is None:
        return ""
    found = element.find(tag)
    return (found.text or "").strip() if found is not None else ""


def read_dependency_list(section: Optional[ElementTree.Element]) -> list:
    """Читает теги dependency из раздела dependencies."""
    if section is None:
        return []
    return [
        {tag: text_of(item, tag) for tag in
         ("groupId", "artifactId", "version", "scope", "optional")}
        for item in section.findall("dependency")
    ]


def read_root(data: bytes) -> ElementTree.Element:
    """Разбирает XML и возвращает корневой элемент без пространств имён."""
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise RepositoryError(f"invalid pom.xml: {error}") from error
    strip_namespaces(root)
    return root


def read_management(pom: Pom, root: ElementTree.Element) -> None:
    """Читает dependencyManagement: версии и импортируемые BOM."""
    section = root.find("dependencyManagement/dependencies")
    for item in read_dependency_list(section):
        coordinates = f"{item['groupId']}:{item['artifactId']}"
        if item["scope"] == "import":
            pom.imports.append(f"{coordinates}:{item['version']}")
        else:
            pom.managed[coordinates] = item["version"]


def parse_pom(data: bytes) -> Pom:
    """Разбирает текст pom.xml."""
    root = read_root(data)
    parent = root.find("parent")
    pom = Pom(
        group=text_of(root, "groupId") or text_of(parent, "groupId"),
        artifact=text_of(root, "artifactId"),
        version=text_of(root, "version") or text_of(parent, "version"),
    )
    if parent is not None:
        pom.parent = ":".join(
            text_of(parent, tag)
            for tag in ("groupId", "artifactId", "version")
        )
    properties = root.find("properties")
    if properties is not None:
        pom.properties = {item.tag: (item.text or "").strip()
                          for item in properties}
    read_management(pom, root)
    pom.dependencies = read_dependency_list(root.find("dependencies"))
    return pom


def load_chain(base: str, coordinates: str) -> List[Pom]:
    """Загружает pom.xml пакета и всех его родителей, ближние первыми."""
    chain = [parse_pom(download(pom_url(base, coordinates)))]
    while chain[-1].parent and len(chain) <= MAX_PARENTS:
        chain.append(parse_pom(download(pom_url(base, chain[-1].parent))))
    return chain


def merged_values(chain: List[Pom]) -> tuple:
    """Собирает свойства и управляемые версии; ближний pom главнее."""
    properties: Dict[str, str] = {}
    managed: Dict[str, str] = {}
    for pom in reversed(chain):
        properties.update(pom.properties)
        managed.update(pom.managed)
    own = chain[0]
    for prefix in ("project.", "pom.", ""):
        properties[prefix + "version"] = own.version
        properties[prefix + "groupId"] = own.group
        properties[prefix + "artifactId"] = own.artifact
    return properties, managed


def substitute(text: str, properties: Dict[str, str]) -> str:
    """Подставляет значения ${свойство}; неизвестные оставляет."""
    for _ in range(MAX_PARENTS):
        new_text = PLACEHOLDER.sub(
            lambda found: properties.get(found.group(1), found.group(0)),
            text,
        )
        if new_text == text:
            break
        text = new_text
    return text


def to_dependency(item: Dict[str, str], properties: dict,
                  managed: dict) -> Dependency:
    """Превращает запись из pom.xml в зависимость с итоговой версией."""
    group = substitute(item["groupId"], properties)
    artifact = substitute(item["artifactId"], properties)
    version = item["version"] or managed.get(f"{group}:{artifact}", "")
    return Dependency(
        group=group,
        artifact=artifact,
        version=substitute(version, properties) or "?",
        scope=item["scope"] or "compile",
        optional=item["optional"] == "true",
    )


def imported_versions(base: str, chain: List[Pom],
                      properties: Dict[str, str]) -> Dict[str, str]:
    """Загружает BOM из scope import и возвращает их версии."""
    versions: Dict[str, str] = {}
    for pom in reversed(chain):
        for coordinates in pom.imports:
            bom_chain = load_chain(base, substitute(coordinates, properties))
            bom_properties, bom_managed = merged_values(bom_chain)
            versions.update({key: substitute(value, bom_properties)
                             for key, value in bom_managed.items()})
    return versions


def direct_dependencies(base: str, coordinates: str) -> List[Dependency]:
    """Возвращает прямые зависимости пакета из репозитория base."""
    chain = load_chain(base, coordinates)
    properties, managed = merged_values(chain)
    managed = {**imported_versions(base, chain, properties), **managed}
    return [to_dependency(item, properties, managed)
            for item in chain[0].dependencies]


class MavenSource:
    """Источник зависимостей для обхода графа.

    Берутся только зависимости, которые Maven переносит транзитивно:
    область compile или runtime и без optional. Пакеты, чей pom.xml
    не удалось получить, становятся листьями, причина запоминается.
    """

    def __init__(self, base: str) -> None:
        """Запоминает адрес репозитория."""
        self.base = base
        self.problems: Dict[str, str] = {}

    def children(self, coordinates: str) -> List[str]:
        """Возвращает транзитивные прямые зависимости пакета."""
        try:
            found = direct_dependencies(self.base, coordinates)
        except RepositoryError as error:
            self.problems[coordinates] = str(error)
            return []
        return [item.coordinates() for item in found
                if item.scope in TRANSITIVE_SCOPES and not item.optional]
