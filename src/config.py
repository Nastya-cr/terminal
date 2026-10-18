"""Параметры запуска эмулятора."""

import argparse


def create_parser():
    """Создаёт парсер параметров запуска эмулятора.

    Описывает доступные параметры командной строки и их значения по
    умолчанию. Сам разбор параметров здесь ещё не выполняется.

    Returns:
        argparse.ArgumentParser: Объект с правилами разбора параметров запуска.
    """
    parser = argparse.ArgumentParser(
        description="Эмулятор UNIX-оболочки",
    )
    parser.add_argument(
        "--vfs",
        default="examples/vfs.xml",
        help="путь к XML-файлу VFS",
    )
    parser.add_argument(
        "--prompt",
        default="$ ",
        help="приглашение к вводу",
    )
    parser.add_argument(
        "--log",
        default="shell-log.xml",
        help="путь к XML-файлу журнала",
    )
    parser.add_argument(
        "--startup",
        help="путь к стартовому скрипту",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="выполнить стартовый скрипт без GUI",
    )
    return parser


def parse_args(argv=None):
    """Разбирает параметры запуска эмулятора.

    Если ``argv`` не передан, параметры читаются из команды, которой была
    запущена программа.

    Args:
        argv: Список параметров или ``None`` для чтения из командной строки.

    Returns:
        argparse.Namespace: Полученные настройки эмулятора.
    """
    return create_parser().parse_args(argv)


def print_configuration(args):
    """Печатает полученные настройки в обычный терминал.

    Отладочный вывод подтверждает, что параметры командной строки были
    прочитаны правильно.

    Args:
        args: Настройки, возвращённые функцией :func:`parse_args`.
    """
    print("Параметры запуска:")
    print(f"  VFS: {args.vfs}")
    print(f"  Приглашение: {args.prompt!r}")
    print(f"  Лог: {args.log}")
    print(f"  Стартовый скрипт: {args.startup or '-'}")
    print(f"  Режим без GUI: {'да' if args.headless else 'нет'}")
