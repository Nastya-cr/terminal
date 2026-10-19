"""Тесты конфигурации и команд."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as et

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from shell import Shell, XmlLogger 
from vfs import VirtualFileSystem 


PROJECT = Path(__file__).parents[1]


class ShellTest(unittest.TestCase):
    """Проверяет логику без GUI."""

    def setUp(self):
        self.vfs = VirtualFileSystem.load(PROJECT / "examples/vfs.xml")
        self.shell = Shell(self.vfs)

    def test_environment_variable_is_expanded(self):
        os.environ["EMU_TEST_DIR"] = "/home/student"
        result = self.shell.execute("cd $EMU_TEST_DIR")
        self.assertTrue(result.ok)
        self.assertEqual(self.shell.cwd, "/home/student")

    def test_error_is_written_to_xml(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "log.xml"
            Shell(logger=XmlLogger(log_path)).execute("unknown")
            root = et.parse(log_path).getroot()
            self.assertEqual(
                root.findtext("event/error"),
                "unknown: команда не найдена",
            )

    def test_script_stops_on_first_error(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "start.txt"
            script.write_text("ls\nunknown\ncd /\n", encoding="utf-8")
            dialogs = self.shell.run_script(script)
            self.assertEqual([item[0] for item in dialogs], ["ls", "unknown"])

    def test_ls_and_cd(self):
        self.assertIn("student/", self.shell.execute("ls /home").output)
        self.assertTrue(self.shell.execute("cd /home/student").ok)
        self.assertIn("notes.txt", self.shell.execute("ls").output)

    def test_cat_and_tac(self):
        cat_result = self.shell.execute("cat /readme.txt")
        tac_result = self.shell.execute("tac /readme.txt")
        self.assertTrue(
            cat_result.output.startswith("Первая строка"),
        )
        self.assertTrue(
            tac_result.output.startswith("Третья строка"),
        )

    def test_command_errors(self):
        self.assertFalse(self.shell.execute("cd /readme.txt").ok)
        self.assertFalse(self.shell.execute("cat /missing.txt").ok)
        self.assertFalse(self.shell.execute("tac /home").ok)

    def test_chown_changes_only_memory(self):
        source = PROJECT / "examples/vfs.xml"
        original = source.read_bytes()
        result = self.shell.execute("chown teacher /readme.txt")
        self.assertTrue(result.ok)
        self.assertEqual(self.vfs.get_node("/readme.txt").owner, "teacher")
        self.assertEqual(source.read_bytes(), original)

    def test_rmdir_removes_empty_directory(self):
        result = self.shell.execute("rmdir /empty")
        self.assertTrue(result.ok)
        self.assertNotIn("empty", self.vfs.root.children)

    def test_rmdir_rejects_unsafe_targets(self):
        self.assertFalse(self.shell.execute("rmdir /").ok)
        self.assertFalse(self.shell.execute("rmdir /home").ok)
        self.shell.execute("cd /empty")
        self.assertFalse(self.shell.execute("rmdir /empty").ok)


if __name__ == "__main__":
    unittest.main()
