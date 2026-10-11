"""Тесты загрузки VFS."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from vfs import VfsError, VirtualFileSystem  # noqa: E402


PROJECT = Path(__file__).parents[1]


class VirtualFileSystemTest(unittest.TestCase):
    """Проверяет XML, пути и данные."""

    def test_loads_text_and_binary_files(self):
        vfs = VirtualFileSystem.load(PROJECT / "examples/vfs.xml")
        self.assertIn(
            "Первая".encode(),
            vfs.get_node("/readme.txt").content,
        )
        self.assertEqual(vfs.get_node("/data.bin").content, bytes(range(5)))

    def test_normalizes_relative_path(self):
        vfs = VirtualFileSystem.load(PROJECT / "examples/vfs.xml")
        node = vfs.get_node("../student/notes.txt", "/home/student")
        self.assertEqual(node.name, "notes.txt")

    def test_reports_invalid_xml(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.xml"
            path.write_text("<broken>", encoding="utf-8")
            with self.assertRaises(VfsError):
                VirtualFileSystem.load(path)

    def test_reports_missing_file(self):
        with self.assertRaisesRegex(VfsError, "файл не найден"):
            VirtualFileSystem.load("missing.xml")


if __name__ == "__main__":
    unittest.main()
