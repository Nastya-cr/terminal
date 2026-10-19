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
        """Проверяет, успешно ли выполнилась команда.

        Returns:
            bool: ``True``, если ошибки нет.
        """
        return not self.error


class XmlLogger:
    """Сохраняет события вызова команд в XML."""

    def __init__(self, path):
        """Создаёт журнал команд.

        Args:
            path: Путь к XML-файлу журнала.
        """
        self.path = Path(path)
        self.root = et.Element("log")

    def write(self, command, error=""):
        """Записывает команду и её ошибку в XML-журнал.

        Args:
            command: Строка, введённая пользователем.
            error: Текст ошибки или пустая строка.
        """
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
        """Подготавливает командный интерпретатор.

        Args:
            vfs: Загруженная виртуальная файловая система.
            logger: XML-журнал команд или ``None``.
        """
        self.vfs = vfs
        self.logger = logger
        self.cwd = "/"

    def execute(self, command_line):
        """Разбирает и выполняет одну введённую строку.

        Args:
            command_line: Команда вместе с её аргументами.

        Returns:
            CommandResult: Результат, ошибка или команда выхода.
        """
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
        """Выполняет команды из файла до ошибки или ``exit``.

        Args:
            path: Путь к файлу с командами.

        Returns:
            list: Выполненные команды вместе с их результатами.

        Raises:
            OSError: Если файл со скриптом невозможно прочитать.
        """
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
        """Разделяет введённую строку на команду и аргументы.

        Перед разделением раскрывает переменные окружения, например ``$HOME``.

        Args:
            command_line: Исходная строка пользователя.

        Returns:
            list: Команда и её аргументы отдельными строками.

        Raises:
            ValueError: Если в строке неправильно расставлены кавычки.
        """
        expanded = os.path.expandvars(command_line)
        return shlex.split(expanded)

    def _dispatch(self, parts):
        """Выбирает функцию для введённой команды.

        Args:
            parts: Список из названия команды и её аргументов.

        Returns:
            CommandResult: Результат выбранной команды.
        """
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
        """Показывает файл или содержимое каталога.

        Args:
            args: Флаг ``-l`` и путь, если они указаны.

        Returns:
            CommandResult: Список имён или сообщение об ошибке.
        """
        long_format = bool(args and args[0] == "-l")
        if long_format:
            args = args[1:]
        if len(args) > 1:
            message = "ls: укажите не более одного пути"
            return CommandResult(error=message)
        path = args[0] if args else self.cwd
        try:
            node = self.vfs.get_node(path, self.cwd)
        except VfsError as error:
            return CommandResult(error=f"ls: {error}")
        if not node.is_directory:
            if long_format:
                return CommandResult(
                    output=f"-  {node.owner}  {node.name}",
                )
            return CommandResult(output=node.name)
        names = []
        for name, child in sorted(node.children.items()):
            shown_name = f"{name}/" if child.is_directory else name
            if long_format:
                kind = "d" if child.is_directory else "-"
                names.append(f"{kind}  {child.owner}  {shown_name}")
            else:
                names.append(shown_name)
        separator = "\n" if long_format else "  "
        return CommandResult(output=separator.join(names))

    def _cd(self, args):
        """Изменяет текущий каталог VFS.

        Args:
            args: Пустой список или список с одним путём.

        Returns:
            CommandResult: Пустой результат или сообщение об ошибке.
        """
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
        """Читает указанные файлы по порядку.

        Args:
            args: Список путей к файлам.

        Returns:
            CommandResult: Содержимое файлов или сообщение об ошибке.
        """
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
        """Читает строки файлов в обратном порядке.

        Args:
            args: Список путей к файлам.

        Returns:
            CommandResult: Перевёрнутые строки или сообщение об ошибке.
        """
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
        """Получает текст файла для команд ``cat`` и ``tac``.

        Args:
            path: Путь к файлу в VFS.
            command: Название команды для текста ошибки.

        Returns:
            tuple: Текст файла и пустая строка либо текст ошибки.
        """
        try:
            node = self.vfs.get_node(path, self.cwd)
        except VfsError as error:
            return "", f"{command}: {error}"
        if node.is_directory:
            return "", f"{command}: это каталог: {path}"
        return node.content.decode("utf-8", errors="replace"), ""

    def _chown(self, args):
        """Изменяет владельца файлов и каталогов в памяти.

        Args:
            args: Имя владельца и пути к изменяемым узлам.

        Returns:
            CommandResult: Пустой результат или сообщение об ошибке.
        """
        if not args:
            return CommandResult(
                error="chown: укажите владельца и путь",
            )

        owner, *paths = args

        if not paths:
            return CommandResult(
                error="chown: укажите владельца и путь",
            )
        owner, paths = args[0], args[1:]
        if not owner:
            message = "chown: пустое имя владельца"
            return CommandResult(error=message)
        for path in paths:
            try:
                node = self.vfs.get_node(path, self.cwd)
                node.owner = owner
            except VfsError as error:
                return CommandResult(error=f"chown: {error}")
        return CommandResult()

    def _rmdir(self, args):
        """Удаляет указанные пустые каталоги из памяти.

        Args:
            args: Список путей к каталогам.

        Returns:
            CommandResult: Пустой результат или сообщение об ошибке.
        """
        if not args:
            message = "rmdir: укажите каталог"
            return CommandResult(error=message)
        for path in args:
            error = self._remove_directory(path)
            if error:
                return CommandResult(error=error)
        return CommandResult()

    def _remove_directory(self, path):
        """Проверяет и удаляет один каталог.

        Args:
            path: Путь к удаляемому каталогу.

        Returns:
            str: Пустая строка при успехе или текст ошибки.
        """
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
        """Передаёт выполненную команду в XML-журнал.

        Args:
            command: Введённая команда.
            error: Текст возникшей ошибки.
        """
        if self.logger:
            self.logger.write(command, error)
