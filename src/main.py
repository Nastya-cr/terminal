"""Графический интерфейс эмулятора."""

import getpass
from pathlib import Path
import socket
import sys
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from config import parse_args, print_configuration
from shell import Shell, XmlLogger
from vfs import VfsError, VirtualFileSystem


class Terminal:
    """Окно с историей и строкой ввода."""

    def __init__(self, root, shell, prompt, startup=None):
        self.root = root
        self.shell = shell
        self.prompt_text = prompt
        self._configure_window()
        self._create_output()
        self._create_input()
        self.write("UNIX Shell Emulator\nВведите команду.\n\n")
        if startup:
            self.root.after(0, lambda: self.run_script(startup))

    def _configure_window(self):
        username = getpass.getuser()
        hostname = socket.gethostname()
        self.root.title(f"Эмулятор - [{username}@{hostname}]")
        self.root.geometry("800x500")
        self.root.minsize(500, 300)
        self.root.configure(bg="#1e1e1e")

    def _create_output(self):
        self.output = ScrolledText(
            self.root,
            bg="#1e1e1e",
            fg="white",
            font=("Menlo", 13),
            state="disabled",
            wrap="word",
        )
        self.output.pack(fill="both", expand=True, padx=10, pady=10)

    def _create_input(self):
        frame = tk.Frame(self.root, bg="#1e1e1e")
        frame.pack(side="bottom", fill="x", padx=10, pady=10)
        tk.Label(
            frame,
            text=self.prompt_text,
            bg="#1e1e1e",
            fg="#80ff80",
            font=("Menlo", 13),
        ).pack(side="left")
        self.command = tk.Entry(
            frame,
            bg="#303030",
            fg="white",
            insertbackground="white",
            font=("Menlo", 13),
        )
        self.command.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self.command.bind("<Return>", self.execute)
        self.command.focus_set()

    def write(self, text):
        """Добавляет текст в историю команд."""
        self.output.config(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.config(state="disabled")

    def execute(self, event=None):
        """Обрабатывает введённую строку."""
        command = self.command.get()
        self.command.delete(0, "end")
        self._show_result(command, self.shell.execute(command))

    def _show_result(self, command, result):
        self.write(f"{self.prompt_text}{command}\n")
        if result.output:
            self.write(f"{result.output}\n")
        if result.error:
            self.write(f"Ошибка: {result.error}\n")
        self.write("\n")
        if result.should_exit:
            self.root.destroy()

    def run_script(self, path):
        """Показывает скрипт как диалог."""
        try:
            dialogs = self.shell.run_script(path)
        except OSError as error:
            message = (
                f"Ошибка стартового скрипта: {error}\n"
            )
            self.write(message)
            return
        for command, result in dialogs:
            self._show_result(command, result)


def run_headless(shell, prompt, startup):
    """Выполняет сценарий без создания окна."""
    if not startup:
        message = "Для --headless нужен параметр --startup"
        print(message, file=sys.stderr)
        return 2
    try:
        dialogs = shell.run_script(startup)
    except OSError as error:
        message = f"Ошибка стартового скрипта: {error}"
        print(message, file=sys.stderr)
        return 1
    for command, result in dialogs:
        print(f"{prompt}{command}")
        print(result.output or result.error)
    return 0 if not dialogs or dialogs[-1][1].ok else 1


def main(argv=None):
    """Запускает настроенный эмулятор."""
    args = parse_args(argv)
    print_configuration(args)
    try:
        vfs = VirtualFileSystem.load(args.vfs)
    except VfsError as error:
        print(f"Ошибка загрузки VFS: {error}", file=sys.stderr)
        return 1
    shell = Shell(vfs, XmlLogger(Path(args.log)))
    if args.headless:
        return run_headless(shell, args.prompt, args.startup)
    root = tk.Tk()
    Terminal(root, shell, args.prompt, args.startup)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
