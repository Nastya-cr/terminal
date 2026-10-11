"""Виртуальная файловая система в памяти."""

import base64
from dataclasses import dataclass, field
import posixpath
from pathlib import Path
import xml.etree.ElementTree as et


class VfsError(Exception):
    """Ошибка загрузки или использования VFS."""


@dataclass
class Node:
    """Файл или каталог VFS."""

    name: str
    owner: str = "root"
    content: bytes | None = None
    children: dict = field(default_factory=dict)

    @property
    def is_directory(self):
        """Возвращает True для каталога."""
        return self.content is None


class VirtualFileSystem:
    """Хранит VFS, загруженную из XML."""

    def __init__(self, name, root):
        self.name = name
        self.root = root

    @classmethod
    def load(cls, path):
        """Загружает и проверяет XML-файл VFS."""
        source = Path(path)
        try:
            xml_root = et.fromstring(source.read_bytes())
        except FileNotFoundError as error:
            raise VfsError(f"файл не найден: {source}") from error
        except (OSError, et.ParseError) as error:
            message = f"не удалось прочитать XML: {error}"
            raise VfsError(message) from error
        if xml_root.tag != "filesystem":
            message = (
                "ожидался корневой элемент filesystem"
            )
            raise VfsError(message)
        roots = list(xml_root)
        if len(roots) != 1 or roots[0].tag != "directory":
            message = (
                "нужен ровно один корневой каталог"
            )
            raise VfsError(message)
        root = cls._read_node(roots[0], is_root=True)
        return cls(xml_root.get("name", source.stem), root)

    @classmethod
    def _read_node(cls, element, is_root=False):
        name = element.get("name", "")
        if not name or (not is_root and "/" in name):
            message = "неверное имя узла"
            raise VfsError(message)
        owner = element.get("owner", "root")
        if element.tag == "file":
            return Node(name, owner, cls._read_content(element))
        if element.tag != "directory":
            message = f"неизвестный элемент: {element.tag}"
            raise VfsError(message)
        node = Node(name, owner)
        for child in element:
            parsed = cls._read_node(child)
            if parsed.name in node.children:
                message = f"повторяющееся имя: {parsed.name}"
                raise VfsError(message)
            node.children[parsed.name] = parsed
        return node

    @staticmethod
    def _read_content(element):
        text = element.text or ""
        encoding = element.get("encoding", "text")
        if encoding == "text":
            return text.encode("utf-8")
        if encoding == "base64":
            try:
                return base64.b64decode(text, validate=True)
            except ValueError as error:
                message = "неверные данные base64"
                raise VfsError(message) from error
        raise VfsError(f"неизвестная кодировка: {encoding}")

    @staticmethod
    def normalize(path, cwd="/"):
        """Нормализует путь."""
        combined = path if path.startswith("/") else posixpath.join(cwd, path)
        normalized = posixpath.normpath(combined)
        return normalized if normalized.startswith("/") else f"/{normalized}"

    def get_node(self, path, cwd="/"):
        """Находит узел по пути."""
        normalized = self.normalize(path, cwd)
        node = self.root
        for part in normalized.strip("/").split("/"):
            if not part:
                continue
            if not node.is_directory or part not in node.children:
                prefix = "нет такого файла или каталога"
                message = f"{prefix}: {path}"
                raise VfsError(message)
            node = node.children[part]
        return node

    def get_parent(self, path, cwd="/"):
        """Возвращает родителя и путь."""
        normalized = self.normalize(path, cwd)
        if normalized == "/":
            message = (
                "у корневого каталога нет родителя"
            )
            raise VfsError(message)
        parent_path, name = posixpath.split(normalized)
        parent = self.get_node(parent_path or "/")
        return parent, name, normalized
