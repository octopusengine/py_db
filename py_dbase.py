"""Command-line entry point for the pyDb SQLite emulator."""

import argparse
import json
import os

from lib.wrapp_dbase3 import Db3, __version__
from lib.wrapp_terminal import Terminal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "py_base.json")
TERM = Terminal()


def load_config():
    """Load the data directory and default database from py_base.json."""

    with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    data_path = config.get("data_path")
    default_database = config.get("default_database")
    if not isinstance(data_path, str) or not data_path:
        raise ValueError("'data_path' must be a non-empty string")
    if not isinstance(default_database, str) or not default_database:
        raise ValueError("'default_database' must be a non-empty string")
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
        metavar="DEFINITION.json",
        help="create a table from a JSON definition in the configured data directory",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="list tables in the selected database and exit",
    )
    return parser.parse_args()


def data_file(data_dir, filename):
    """Return a data-directory path while preventing directory traversal."""

    clean_name = os.path.basename(filename)
    if clean_name != filename or clean_name in ("", ".", ".."):
        raise ValueError("filename must not contain a directory path")
    return os.path.join(data_dir, clean_name)


def create_table_from_definition(database, data_dir, filename):
    """Read a JSON definition and ask the database wrapper to create its table."""

    definition_path = data_file(data_dir, filename)
    if not os.path.isfile(definition_path):
        raise FileNotFoundError(f"Definition file '{definition_path}' was not found.")

    with open(definition_path, "r", encoding="utf-8") as definition_file:
        definition = json.load(definition_file)

    columns = definition.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ValueError("JSON definition must contain a non-empty 'columns' list.")

    fields = []
    for column in columns:
        if not isinstance(column, dict) or not isinstance(column.get("field"), str):
            raise ValueError("Each item in 'columns' must contain a string 'field'.")
        fields.append(column["field"])

    fallback_table_name = os.path.splitext(os.path.basename(filename))[0]
    table_name = definition.get("table", fallback_table_name)
    database.create_table_from_fields(table_name, fields)


def main():
    """Configure and run the interactive database wrapper."""

    try:
        arguments = parse_arguments()
        config = load_config()
        data_dir = os.path.abspath(os.path.join(BASE_DIR, config["data_path"]))
        os.makedirs(data_dir, exist_ok=True)
        db_file = data_file(data_dir, arguments.name or config["default_database"])
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"Configuration error: {error}") from error

    database = None
    try:
        database = Db3(
            db_file,
            export_dir=os.path.join(BASE_DIR, "export"),
            terminal=TERM,
        )
        if arguments.crea:
            create_table_from_definition(database, data_dir, arguments.crea)

        if arguments.list:
            database.cmd_show()
            return

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
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"Start error: {error}") from error
    finally:
        if database is not None:
            database.close()


if __name__ == "__main__":
    main()
