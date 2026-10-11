"""Логика командного интерпретатора."""

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import shlex
import xml.etree.ElementTree as et

from vfs import VfsError


@dataclass
class CommandResult:
    """Результат выполнения одной команды."""

    output: str = ""
    error: str = ""
    should_exit: bool = False

    @property
    def ok(self):
        """Проверяет отсутствие ошибки."""
        return not self.error


class XmlLogger:
    """Сохраняет события вызова команд в XML."""

    def __init__(self, path):
        self.path = Path(path)
        self.root = et.Element("log")

    def write(self, command, error=""):
        """Добавляет событие в журнал."""
        event = et.SubElement(
            self.root,
            "event",
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
        et.SubElement(event, "command").text = command
        et.SubElement(event, "error").text = error
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tree = et.ElementTree(self.root)
        et.indent(tree, space="  ")
        tree.write(self.path, encoding="utf-8", xml_declaration=True)


class Shell:
    """Разбирает и выполняет команды."""

    def __init__(self, vfs=None, logger=None):
        self.vfs = vfs
        self.logger = logger
        self.cwd = "/"

    def execute(self, command_line):
        """Выполняет одну строку."""
        parts = []
        try:
            parts = self._parse(command_line)
            result = self._dispatch(parts)
        except (ValueError, VfsError) as error:
            message = f"Ошибка разбора: {error}"
            result = CommandResult(error=message)
        if command_line.strip():
            self._log(command_line, result.error)
        return result

    def run_script(self, path):
        """Выполняет скрипт до ошибки или exit."""
        dialogs = []
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            command = line.strip()
            if not command or command.startswith("#"):
                continue
            result = self.execute(command)
            dialogs.append((command, result))
            if not result.ok or result.should_exit:
                break
        return dialogs

    @staticmethod
    def _parse(command_line):
        expanded = os.path.expandvars(command_line)
        return shlex.split(expanded)

    def _dispatch(self, parts):
        if not parts:
            return CommandResult()
        name, args = parts[0], parts[1:]
        commands = {
            "ls": self._ls,
            "cd": self._cd,
            "cat": self._cat,
            "tac": self._tac,
            "chown": self._chown,
            "rmdir": self._rmdir,
        }
        if name in commands:
            return commands[name](args)
        if name == "exit" and not args:
            return CommandResult(should_exit=True)
        if name == "exit":
            message = (
                "exit: аргументы не поддерживаются"
            )
            return CommandResult(error=message)
        message = f"{name}: команда не найдена"
        return CommandResult(error=message)

    def _ls(self, args):
        if len(args) > 1:
            message = "ls: укажите не более одного пути"
            return CommandResult(error=message)
        path = args[0] if args else self.cwd
        try:
            node = self.vfs.get_node(path, self.cwd)
        except VfsError as error:
            return CommandResult(error=f"ls: {error}")
        if not node.is_directory:
            return CommandResult(output=node.name)
        names = []
        for name, child in sorted(node.children.items()):
            names.append(f"{name}/" if child.is_directory else name)
        return CommandResult(output="  ".join(names))

    def _cd(self, args):
        if len(args) > 1:
            message = "cd: укажите не более одного пути"
            return CommandResult(error=message)
        path = args[0] if args else "/"
        try:
            node = self.vfs.get_node(path, self.cwd)
        except VfsError as error:
            return CommandResult(error=f"cd: {error}")
        if not node.is_directory:
            return CommandResult(error=f"cd: не каталог: {path}")
        self.cwd = self.vfs.normalize(path, self.cwd)
        return CommandResult()

    def _cat(self, args):
        if not args:
            message = "cat: укажите хотя бы один файл"
            return CommandResult(error=message)
        contents = []
        for path in args:
            text, error = self._file_text(path, "cat")
            if error:
                return CommandResult(error=error)
            contents.append(text)
        return CommandResult(output="".join(contents).rstrip("\n"))

    def _tac(self, args):
        if not args:
            message = "tac: укажите хотя бы один файл"
            return CommandResult(error=message)
        contents = []
        for path in args:
            text, error = self._file_text(path, "tac")
            if error:
                return CommandResult(error=error)
            contents.append("\n".join(reversed(text.splitlines())))
        return CommandResult(output="\n".join(contents))

    def _file_text(self, path, command):
        try:
            node = self.vfs.get_node(path, self.cwd)
        except VfsError as error:
            return "", f"{command}: {error}"
        if node.is_directory:
            return "", f"{command}: это каталог: {path}"
        return node.content.decode("utf-8", errors="replace"), ""

    def _chown(self, args):
        if len(args) < 2:
            message = "chown: нужны владелец и путь"
            return CommandResult(error=message)
        owner, paths = args[0], args[1:]
        if not owner:
            message = "chown: пустое имя владельца"
            return CommandResult(error=message)
        for path in paths:
            try:
                self.vfs.get_node(path, self.cwd).owner = owner
            except VfsError as error:
                return CommandResult(error=f"chown: {error}")
        return CommandResult()

    def _rmdir(self, args):
        if not args:
            message = "rmdir: укажите каталог"
            return CommandResult(error=message)
        for path in args:
            error = self._remove_directory(path)
            if error:
                return CommandResult(error=error)
        return CommandResult()

    def _remove_directory(self, path):
        try:
            parent, name, normalized = self.vfs.get_parent(path, self.cwd)
            node = self.vfs.get_node(normalized)
        except VfsError as error:
            return f"rmdir: {error}"
        if not node.is_directory:
            return f"rmdir: не каталог: {path}"
        if node.children:
            return f"rmdir: каталог не пуст: {path}"
        prefix = normalized.rstrip("/") + "/"
        if self.cwd == normalized or self.cwd.startswith(prefix):
            return f"rmdir: каталог используется: {path}"
        del parent.children[name]
        return ""

    def _log(self, command, error):
        if self.logger:
            self.logger.write(command, error)
