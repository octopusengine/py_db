"""dBASE III-style command wrapper around a SQLite database."""

import csv
import json
import os
import sqlite3
import xml.etree.ElementTree as ET

from .wrapp_terminal import Terminal

__version__ = "0.3.1"

COMMANDS = {
    "CREA": "CREATE",
    "INSE": "INSERT",
    "SELE": "SELECT",
    "DELE": "DELETE",
    "DROP": "DROP",
    "LIST": "LIST",
    "HELP": "HELP",
    "EXIT": "EXIT",
    "RUN": "RUN",
    "SHOW": "SHOW",
    "USE": "USE",
    "SQL": "SQL",
    "STRU": "STRUCT",
    "MODI": "MODIF",
    "EXPO": "EXPORT",
}

HELP_LINES = (
    ("CREATE", " <table_name>    - Creates a table with default columns."),
    ("INSERT", " (columns) VALUES (values) - Inserts a row into the active table."),
    ("SELECT", " [<col1> <col2> ...] - Displays active-table rows."),
    ("DELETE", " WHERE <condition> - Deletes active-table rows."),
    ("DROP", " <table_name>      - Removes a table after confirmation."),
    ("LIST", " [<col1> <col2> ...] - Lists selected active-table columns."),
    ("USE", " <table>            - Selects the active table."),
    ("SHOW", "                   - Lists tables in the current database."),
    ("STRUCT", "                 - Displays the active table structure."),
    ("MODIF", " ADD <col> <type> - Adds a column to the active table."),
    ("MODIF", " DROP <col>       - Removes a column from the active table."),
    ("SQL", ' "<query>"          - Executes a raw SQL query.'),
    ("RUN", " <file>.dbs         - Executes commands from a script."),
    ("HELP", "                   - Displays this help message."),
    ("EXIT", "                   - Exits the emulator."),
)


def _quote_identifier(name):
    """Quote a SQLite identifier."""

    if not isinstance(name, str) or not name:
        raise ValueError("Identifier must be a non-empty string.")
    return '"' + name.replace('"', '""') + '"'


def _valid_identifier(name):
    return (
        isinstance(name, str)
        and bool(name)
        and not name[0].isdigit()
        and name.replace("_", "").isalnum()
    )


class Db3:
    """Interactive dBASE-style command interpreter backed by SQLite."""

    COMMANDS = COMMANDS

    def __init__(self, db_file="main.sql", export_dir="export", debug=True, terminal=None):
        self.db_file = db_file
        self.export_dir = export_dir
        self.debug_mode = debug
        self.term = terminal or Terminal()
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self.active_table = None
        os.makedirs(self.export_dir, exist_ok=True)

    def close(self):
        self.conn.close()

    def debug(self, mode):
        self.debug_mode = bool(mode)
        print("Debug mode enabled." if self.debug_mode else "Debug mode disabled.")

    def _debug(self, query):
        if self.debug_mode:
            print(f"DEBUG: Executing SQL -> {query}")

    def execute(self, query, params=(), suppress_debug=False):
        """Execute SQL for callers using the wrapper as a small library."""

        if not suppress_debug:
            self._debug(query)
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor.fetchall()
        except sqlite3.Error as error:
            print(f"SQL Error: {error}")
            return None

    def table_exists(self, table_name):
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return self.cursor.fetchone() is not None

    def create(self, table_name, column_definitions=None):
        if not table_name:
            print("Table name is missing.")
            return False
        columns = column_definitions or "(id INTEGER PRIMARY KEY, data TEXT)"
        query = f"CREATE TABLE {_quote_identifier(table_name)} {columns}"
        if self.execute(query) is None:
            return False
        self.active_table = table_name
        print(f"Table '{table_name}' created and set as active.")
        return True

    def create_table_from_fields(self, table_name, fields):
        """Create a JSON-defined table when it does not already exist."""

        if not _valid_identifier(table_name):
            raise ValueError(f"Invalid table name '{table_name}'.")
        if not fields or any(not _valid_identifier(field) for field in fields):
            raise ValueError("JSON fields must be valid non-empty identifiers.")
        if len(set(fields)) != len(fields):
            raise ValueError("JSON fields must not contain duplicates.")

        definitions = [
            f"{_quote_identifier(field)} {'INTEGER PRIMARY KEY' if field == 'uid' else 'TEXT'}"
            for field in fields
        ]
        query = (
            f"CREATE TABLE IF NOT EXISTS {_quote_identifier(table_name)} "
            f"({', '.join(definitions)})"
        )
        self._debug(query)
        self.cursor.execute(query)
        self.conn.commit()
        print(f"Table '{table_name}' created from JSON definition.")

    def cmd_show(self):
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = self.cursor.fetchall()
        if not tables:
            print("No tables found.")
            return
        self.term.y("Tables in database:")
        for (table_name,) in tables:
            marker = " (ACTIVE)" if table_name == self.active_table else ""
            print(f"- {table_name}{marker}")

    def cmd_use(self, table_name):
        if not table_name:
            print("Table name is missing.")
            return False
        if not self.table_exists(table_name):
            print(f"Table '{table_name}' does not exist.")
            return False
        self.active_table = table_name
        print(f"Using table '{table_name}'. (Active Table Set)")
        return True

    def _active_table_columns(self):
        self.cursor.execute(f"PRAGMA table_info({_quote_identifier(self.active_table)})")
        return [column[1] for column in self.cursor.fetchall()]

    def cmd_list(self, requested_columns=None):
        if self.active_table is None:
            print("No table selected. Use 'USE <table>' first.")
            return

        requested_columns = requested_columns or []
        try:
            available_columns = self._active_table_columns()
            missing_columns = [
                column for column in requested_columns if column not in available_columns
            ]
            if missing_columns:
                print(
                    f"WARNING: Column(s) not found in '{self.active_table}': "
                    + ", ".join(missing_columns)
                )
                return

            column_names = requested_columns or available_columns
            select_columns = ", ".join(_quote_identifier(column) for column in column_names)
            query = f"SELECT {select_columns} FROM {_quote_identifier(self.active_table)}"
            self._debug(query)
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            if not rows:
                print(f"No records found in '{self.active_table}'.")
                return

            self.term.y(" | ".join(column_names))
            print("-" * (len(column_names) * 10))
            for row in rows:
                print(" | ".join(map(str, row)))
        except sqlite3.Error as error:
            print(f"SQL Error: {error}")

    def cmd_struct(self):
        if self.active_table is None:
            print("No table selected. Use 'USE <table>' first.")
            return
        try:
            self.cursor.execute(f"PRAGMA table_info({_quote_identifier(self.active_table)})")
            columns = self.cursor.fetchall()
            if not columns:
                print(f"No columns found in '{self.active_table}'.")
                return
            self.term.y(f"Structure of '{self.active_table}':")
            self.term.y(f"{'Column':<20}{'Type':<10}{'Primary Key'}")
            print("-" * 40)
            for column in columns:
                print(
                    f"{column[1]:<20}{column[2]:<10}"
                    f"{'YES' if column[5] else 'NO'}"
                )
        except sqlite3.Error as error:
            print(f"SQL Error: {error}")

    def modify_table(self, action, column_name, column_type=None):
        if self.active_table is None:
            print("No table selected. Use 'USE <table>' first.")
            return
        action = action.upper()
        if action == "ADD":
            if not column_name or not column_type:
                print("Usage: MODIF ADD <column_name> <column_type>")
                return
            query = (
                f"ALTER TABLE {_quote_identifier(self.active_table)} "
                f"ADD COLUMN {_quote_identifier(column_name)} {column_type}"
            )
            if self.execute(query) is not None:
                print(f"Column '{column_name}' added to '{self.active_table}'.")
            return

        if action != "DROP":
            print("Usage: MODIF ADD <column_name> <column_type>")
            return

        try:
            columns = self._active_table_columns()
            if column_name not in columns:
                print(f"Column '{column_name}' does not exist in '{self.active_table}'.")
                return
            if len(columns) <= 2:
                print("Cannot drop the last column (except primary key).")
                return

            remaining_columns = [column for column in columns if column != column_name]
            temporary_table = f"{self.active_table}_new"
            self.cursor.execute(
                f"CREATE TABLE {_quote_identifier(temporary_table)} AS "
                f"SELECT {', '.join(_quote_identifier(column) for column in remaining_columns)} "
                f"FROM {_quote_identifier(self.active_table)}"
            )
            self.cursor.execute(f"DROP TABLE {_quote_identifier(self.active_table)}")
            self.cursor.execute(
                f"ALTER TABLE {_quote_identifier(temporary_table)} "
                f"RENAME TO {_quote_identifier(self.active_table)}"
            )
            self.conn.commit()
            print(f"Column '{column_name}' removed from '{self.active_table}'.")
        except sqlite3.Error as error:
            print(f"SQL Error: {error}")

    def cmd_delete(self, condition):
        if self.active_table is None:
            print("No table selected. Use 'USE <table>' first.")
            return
        if not condition:
            print("Missing condition for DELETE. Use: DELETE WHERE <condition>")
            return
        query = f"DELETE FROM {_quote_identifier(self.active_table)} {condition}"
        if self.execute(query) is not None:
            print(f"Record(s) deleted from '{self.active_table}'.")

    def cmd_insert(self, values):
        if self.active_table is None:
            print("No table selected. Use 'USE <table>' first.")
            return
        if not values:
            print("Missing values for INSERT.")
            return

        expected_intro = f"INTO {self.active_table}".upper()
        if values.upper().startswith(expected_intro):
            values = values[len(expected_intro):].strip()
        query = f"INSERT INTO {_quote_identifier(self.active_table)} {values}"
        if self.execute(query) is not None:
            print(f"Record inserted into '{self.active_table}'.")

    def cmd_drop(self, table_name):
        if not table_name:
            print("Table name is missing.")
            return
        if not self.table_exists(table_name):
            print(f"Table '{table_name}' does not exist.")
            return
        confirm = input(
            f"Are you sure you want to drop table '{table_name}'? (Y/N): "
        ).strip().upper()
        if confirm != "Y":
            print(f"Operation cancelled. Table '{table_name}' was not dropped.")
            return
        query = f"DROP TABLE {_quote_identifier(table_name)}"
        if self.execute(query) is not None:
            if self.active_table == table_name:
                self.active_table = None
            print(f"Table '{table_name}' dropped.")

    def export(self, table_name, filename, file_format):
        """Export one table to CSV, JSON, or XML."""

        try:
            self.cursor.execute(f"SELECT * FROM {_quote_identifier(table_name)}")
            rows = self.cursor.fetchall()
            column_names = [description[0] for description in self.cursor.description]
        except sqlite3.Error as error:
            print(f"SQL Error: {error}")
            return

        if not rows:
            print(f"WARNING: No data found in '{table_name}', nothing to export.")
            return

        file_path = os.path.join(self.export_dir, filename)
        file_format = file_format.lower()
        try:
            if file_format == "csv":
                with open(file_path, "w", newline="", encoding="utf-8") as export_file:
                    writer = csv.writer(export_file)
                    writer.writerow(column_names)
                    writer.writerows(rows)
            elif file_format == "json":
                data = [dict(zip(column_names, row)) for row in rows]
                with open(file_path, "w", encoding="utf-8") as export_file:
                    json.dump(data, export_file, indent=4, ensure_ascii=False)
            elif file_format == "xml":
                root = ET.Element("table", name=table_name)
                for row in rows:
                    row_element = ET.SubElement(root, "row")
                    for column_name, value in zip(column_names, row):
                        column_element = ET.SubElement(row_element, column_name)
                        column_element.text = "" if value is None else str(value)
                xml_text = ET.tostring(root, encoding="unicode")
                with open(file_path, "w", encoding="utf-8") as export_file:
                    export_file.write('<?xml version="1.0" encoding="utf-8"?>\n')
                    export_file.write(xml_text.replace("</row>", "</row>\n"))
            else:
                print(
                    f"ERROR: Unsupported file format '{file_format}'. "
                    "Use csv, json, or xml."
                )
                return
        except OSError as error:
            print(f"ERROR: Failed to export {file_format.upper()}: {error}")
            return

        print(f"SUCCESS: Data exported to '{file_path}' in {file_format.upper()} format.")

    def export_active(self, filename):
        if self.active_table is None:
            print("No table selected. Use 'USE <table>' first.")
            return
        _, extension = os.path.splitext(filename.lower())
        formats = {".csv": "csv", ".json": "json", ".xml": "xml"}
        file_format = formats.get(extension)
        if file_format is None:
            print("Unknown file extension – please use .csv, .xml or .json.")
            return
        self.export(self.active_table, filename, file_format)

    def run_script(self, filename):
        if not filename.lower().endswith(".dbs"):
            print("Error: Only .dbs script files are allowed.")
            return
        if not os.path.exists(filename):
            print(f"Error: File '{filename}' not found.")
            return
        try:
            with open(filename, "r", encoding="utf-8") as script_file:
                for command in script_file:
                    command = command.strip()
                    if command:
                        print(f"Executing: {command}")
                        if not self.execute_dbase_command(command):
                            break
        except OSError as error:
            print(f"Error executing file: {error}")

    def select(self, condition=""):
        """Compatibility helper that lists active-table rows."""

        if condition:
            print("SELECT conditions are not supported; use SQL for custom queries.")
        self.cmd_list()

    def _show_help(self):
        self.term.y("-------------------")
        self.term.y("Available Commands:")
        self.term.y("-------------------")
        for keyword, description in HELP_LINES:
            print(f"{self.term.style(keyword, fg='bright_yellow', bold=True)}{description}")

    def _execute_raw_sql(self, query):
        if not query:
            print('Usage: SQL "<query>"')
            return
        self._debug(query)
        try:
            self.cursor.execute(query)
            if self.cursor.description:
                column_names = [description[0] for description in self.cursor.description]
                rows = self.cursor.fetchall()
                self.term.y(" | ".join(column_names))
                for row in rows:
                    print(" | ".join(map(str, row)))
            self.conn.commit()
        except sqlite3.Error as error:
            print(f"SQL Error: {error}")

    def execute_dbase_command(self, command):
        """Execute one interactive command; return False for EXIT."""

        command = command.strip()
        if not command:
            return True
        words = command.split(" ", 1)
        command_word = words[0].upper()
        args = words[1].strip() if len(words) > 1 else ""
        command_key = command_word[:4] if len(command_word) >= 4 else command_word[:3]
        base_command = self.COMMANDS.get(command_key)
        if base_command is None:
            print(f"Unknown command: {words[0]}")
            return True

        if base_command == "HELP":
            self._show_help()
        elif base_command == "CREATE":
            table_definition = args.split(" ", 1)
            self.create(
                table_definition[0] if table_definition else "",
                table_definition[1] if len(table_definition) > 1 else None,
            )
        elif base_command == "INSERT":
            self.cmd_insert(args)
        elif base_command in {"LIST", "SELECT"}:
            self.cmd_list(args.split() if args else [])
        elif base_command == "DELETE":
            self.cmd_delete(args)
        elif base_command == "DROP":
            self.cmd_drop(args)
        elif base_command == "USE":
            self.cmd_use(args)
        elif base_command == "SHOW":
            self.cmd_show()
        elif base_command == "STRUCT":
            self.cmd_struct()
        elif base_command == "MODIF":
            parameters = args.split()
            if len(parameters) < 2:
                print("Usage: MODIF ADD <column_name> <column_type>")
            else:
                self.modify_table(
                    parameters[0],
                    parameters[1],
                    parameters[2] if len(parameters) > 2 else None,
                )
        elif base_command == "EXPORT":
            self.export_active(args)
        elif base_command == "RUN":
            if not args:
                print("Filename is missing.")
            else:
                self.run_script(args)
        elif base_command == "SQL":
            self._execute_raw_sql(args)
        elif base_command == "EXIT":
            print("Exiting emulator...")
            return False
        return True
