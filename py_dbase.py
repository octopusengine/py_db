"""Command-line entry point for the pyDb SQLite emulator."""

import argparse
import json
import os
import sqlite3
import sys

from lib.wrapp_dbase3 import Db3, __version__
from lib.wrapp_terminal import Terminal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "py_dbase.json")
TERM = Terminal()


def load_config():
    """Load the data directory, database, and debug setting from py_dbase.json."""

    with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    data_path = config.get("data_path")
    default_database = config.get("default_database")
    debug = config.get("debug", False)
    if not isinstance(data_path, str) or not data_path:
        raise ValueError("'data_path' must be a non-empty string")
    if not isinstance(default_database, str) or not default_database:
        raise ValueError("'default_database' must be a non-empty string")
    if not isinstance(debug, bool):
        raise ValueError("'debug' must be true or false")
    return config


def parse_arguments():
    parser = argparse.ArgumentParser(description="pyDb Emulator")
    parser.add_argument(
        "-v",
        "--ver",
        action="version",
        version=f"%(prog)s {__version__}",
        help="show the pyDb Emulator version and exit",
    )
    parser.add_argument(
        "--name",
        metavar="DATABASE",
        help="database filename stored in the configured data directory",
    )
    parser.add_argument(
        "-c",
        "--crea",
        "--create",
        metavar="DEFINITION.json|.sql",
        help="create tables from a JSON definition or SQL script in the configured data directory",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="list tables in the selected database and exit",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format for --list (default: text)",
    )
    parser.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="format",
        help="shorthand for --format json with --list",
    )
    debug_group = parser.add_mutually_exclusive_group()
    debug_group.add_argument(
        "--debug",
        action="store_true",
        help="print executed SQLite statements",
    )
    debug_group.add_argument(
        "--no-debug",
        action="store_true",
        help="suppress executed SQLite statements",
    )
    arguments = parser.parse_args()
    if arguments.format != "text" and not arguments.list:
        parser.error("--format/--json may only be used with --list")
    if arguments.format == "json" and arguments.crea:
        parser.error("--format json cannot be combined with --create")
    return arguments


def data_file(data_dir, filename):
    """Return a data-directory path while preventing directory traversal."""

    clean_name = os.path.basename(filename)
    if clean_name != filename or clean_name in ("", ".", ".."):
        raise ValueError("filename must not contain a directory path")
    return os.path.join(data_dir, clean_name)


def create_table_from_definition(database, data_dir, filename):
    """Create tables from a JSON definition or a SQL script in the data directory."""

    definition_path = data_file(data_dir, filename)
    if not os.path.isfile(definition_path):
        raise FileNotFoundError(f"Definition file '{definition_path}' was not found.")

    extension = os.path.splitext(filename)[1].lower()
    if extension == ".sql":
        with open(definition_path, "r", encoding="utf-8") as definition_file:
            database.execute_sql_script(definition_file.read())
        return
    if extension != ".json":
        raise ValueError("Definition file must use the .json or .sql extension.")

    with open(definition_path, "r", encoding="utf-8") as definition_file:
        definition = json.load(definition_file)

    columns = definition.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ValueError("JSON definition must contain a non-empty 'columns' list.")

    fallback_table_name = os.path.splitext(os.path.basename(filename))[0]
    table_name = definition.get("table", fallback_table_name)
    database.create_table_from_columns(table_name, columns)


def main():
    """Configure and run the interactive database wrapper."""

    try:
        arguments = parse_arguments()
        config = load_config()
        data_dir = os.path.abspath(os.path.join(BASE_DIR, config["data_path"]))
        os.makedirs(data_dir, exist_ok=True)
        db_file = data_file(data_dir, arguments.name or config["default_database"])
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2

    database = None
    try:
        database = Db3(
            db_file,
            export_dir=os.path.join(BASE_DIR, "export"),
            debug=True if arguments.debug else False if arguments.no_debug else config["debug"],
            terminal=TERM,
        )
        if arguments.crea:
            create_table_from_definition(database, data_dir, arguments.crea)

        if arguments.list:
            database.cmd_show(arguments.format)
            return 0

        print("=" * 50)
        print(
            f"{TERM.style(f'pyDb Emulator v{__version__}', fg='bright_yellow', bold=True)}"
            " | SQLite backend:"
        )
        print(db_file)
        print("=" * 50)
        print("Type 'HELP' for available commands or 'EXIT' to quit.")

        while True:
            command = input(TERM.style("pyDb> ", fg="bright_yellow", bold=True)).strip()
            if not database.execute_dbase_command(command):
                break
        return 0
    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as error:
        print(f"Start error: {error}", file=sys.stderr)
        return 1
    except EOFError:
        print("\nExiting emulator...")
        return 0
    finally:
        if database is not None:
            database.close()


if __name__ == "__main__":
    raise SystemExit(main())
