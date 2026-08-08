"""dBASE III-style command wrapper around a SQLite database."""

import csv
import json
import os
import re
import sqlite3
import xml.etree.ElementTree as ET

from .wrapp_terminal import Terminal

__version__ = "0.4.0"

COMMANDS = {
    "CREA": "CREATE",
    "INSE": "INSERT",
    "SELE": "SELECT",
    "DELE": "DELETE",
    "DROP": "DROP",
    "LIST": "LIST",
    "FIND": "FIND",
    "LOCA": "LOCATE",
    "UPDA": "UPDATE",
    "REPL": "REPLACE",
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
    ("SELECT", " [LIST options]    - Alias for LIST."),
    ("DELETE", " WHERE <condition> - Deletes active-table rows."),
    ("DROP", " <table_name>      - Removes a table after confirmation."),
    ("LIST", " [cols] [WHERE <condition>] [ORDER BY <col> [ASC|DESC]]"),
    ("", " [LIMIT <count> [OFFSET <count>] | PAGE <number> SIZE <count>]"),
    ("FIND", " <condition>      - Finds and displays the first matching record."),
    ("LOCATE", " FOR <condition>  - Alias for FIND using dBASE-style syntax."),
    ("UPDATE", " SET <col>=<value> WHERE <condition> - Updates matching records."),
    ("REPLACE", " <col> WITH <value> FOR <condition> - dBASE-style update."),
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


def _split_sql_items(text):
    """Split comma-separated SQL fragments without splitting quoted values."""

    items, current = [], []
    quote = None
    index = 0
    while index < len(text):
        character = text[index]
        if quote:
            current.append(character)
            if character == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    current.append(text[index + 1])
                    index += 1
                else:
                    quote = None
        elif character in ("'", '"'):
            quote = character
            current.append(character)
        elif character == ",":
            item = "".join(current).strip()
            if not item:
                raise ValueError("Empty value in a comma-separated list.")
            items.append(item)
            current = []
        else:
            current.append(character)
        index += 1

    if quote:
        raise ValueError("Unterminated quoted value.")
    item = "".join(current).strip()
    if not item:
        raise ValueError("Empty value in a comma-separated list.")
    items.append(item)
    return items


def _split_keyword(text, keyword):
    """Split at the first whole keyword outside single or double quotes."""

    quote = None
    upper_keyword = keyword.upper()
    index = 0
    while index <= len(text) - len(keyword):
        character = text[index]
        if quote:
            if character == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    index += 2
                    continue
                quote = None
            index += 1
            continue
        if character in ("'", '"'):
            quote = character
            index += 1
            continue
        before = text[index - 1] if index else " "
        after_index = index + len(keyword)
        after = text[after_index] if after_index < len(text) else " "
        if (
            text[index:after_index].upper() == upper_keyword
            and not (before.isalnum() or before == "_")
            and not (after.isalnum() or after == "_")
        ):
            return text[:index].strip(), text[after_index:].strip()
        index += 1
    return None, None


def _list_clause_matches(text):
    """Locate LIST clauses while ignoring clause-looking quoted SQL values."""

    matches = []
    quote = None
    index = 0
    pattern = re.compile(r"(WHERE|ORDER\s+BY|LIMIT|OFFSET|PAGE|SIZE)\b", re.I)
    while index < len(text):
        character = text[index]
        if quote:
            if character == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    index += 2
                    continue
                quote = None
            index += 1
            continue
        if character in ("'", '"'):
            quote = character
            index += 1
            continue
        previous = text[index - 1] if index else " "
        match = pattern.match(text, index)
        if match and not (previous.isalnum() or previous == "_"):
            matches.append((match.start(), match.end(), match.group(1)))
            index = match.end()
            continue
        index += 1
    return matches


class Db3:
    """Interactive dBASE-style command interpreter backed by SQLite."""

    COMMANDS = COMMANDS

    def __init__(self, db_file="main.sql", export_dir="export", debug=False, terminal=None):
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

    def cmd_show(self, output_format="text"):
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = self.cursor.fetchall()
        table_names = [table_name for (table_name,) in tables]
        if output_format == "json":
            print(
                json.dumps(
                    {"database": os.path.basename(self.db_file), "tables": table_names},
                    ensure_ascii=False,
                )
            )
            return table_names
        if not tables:
            print("No tables found.")
            return table_names
        self.term.y("Tables in database:")
        for (table_name,) in tables:
            marker = " (ACTIVE)" if table_name == self.active_table else ""
            print(f"- {table_name}{marker}")
        return table_names

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

    def _parse_list_arguments(self, arguments):
        """Parse LIST's lightweight WHERE/ORDER/LIMIT and paging clauses."""

        if isinstance(arguments, (list, tuple)):
            arguments = " ".join(arguments)
        arguments = (arguments or "").strip()
        matches = _list_clause_matches(arguments)
        clauses = {}
        columns_part = arguments[: matches[0][0]].strip() if matches else arguments
        for position, match in enumerate(matches):
            clause = re.sub(r"\s+", " ", match[2].upper())
            value_end = matches[position + 1][0] if position + 1 < len(matches) else len(arguments)
            value = arguments[match[1] : value_end].strip()
            if clause in clauses:
                raise ValueError(f"LIST clause '{clause}' may be used only once.")
            if not value:
                raise ValueError(f"LIST clause '{clause}' requires a value.")
            clauses[clause] = value

        allowed_clause_order = ["WHERE", "ORDER BY", "LIMIT", "OFFSET", "PAGE", "SIZE"]
        encountered = [re.sub(r"\s+", " ", match[2].upper()) for match in matches]
        if encountered != sorted(encountered, key=allowed_clause_order.index):
            raise ValueError("LIST clauses must be ordered as WHERE, ORDER BY, LIMIT/OFFSET, PAGE/SIZE.")

        columns = columns_part.replace(",", " ").split() if columns_part else []
        parsed = {"columns": columns, "where": clauses.get("WHERE"), "order_by": None,
                  "limit": None, "offset": 0}
        if "ORDER BY" in clauses:
            parts = clauses["ORDER BY"].split()
            if len(parts) not in (1, 2) or (len(parts) == 2 and parts[1].upper() not in {"ASC", "DESC"}):
                raise ValueError("Use: ORDER BY <column> [ASC|DESC]")
            parsed["order_by"] = (parts[0], parts[1].upper() if len(parts) == 2 else "ASC")

        def positive_integer(value, label, allow_zero=False):
            if not re.fullmatch(r"\d+", value) or (not allow_zero and int(value) == 0):
                comparison = "a non-negative" if allow_zero else "a positive"
                raise ValueError(f"{label} must be {comparison} integer.")
            return int(value)

        if "LIMIT" in clauses:
            parsed["limit"] = positive_integer(clauses["LIMIT"], "LIMIT")
        if "OFFSET" in clauses:
            if parsed["limit"] is None:
                raise ValueError("OFFSET requires LIMIT.")
            parsed["offset"] = positive_integer(clauses["OFFSET"], "OFFSET", allow_zero=True)
        has_page = "PAGE" in clauses or "SIZE" in clauses
        if has_page:
            if "PAGE" not in clauses or "SIZE" not in clauses:
                raise ValueError("Paging requires both PAGE <number> and SIZE <count>.")
            if parsed["limit"] is not None:
                raise ValueError("Use either LIMIT/OFFSET or PAGE/SIZE, not both.")
            page = positive_integer(clauses["PAGE"], "PAGE")
            size = positive_integer(clauses["SIZE"], "SIZE")
            parsed["limit"] = size
            parsed["offset"] = (page - 1) * size
        return parsed

    def _display_rows(self, column_names, rows):
        self.term.y(" | ".join(column_names))
        print("-" * (len(column_names) * 10))
        for row in rows:
            print(" | ".join("" if value is None else str(value) for value in row))

    def cmd_list(self, arguments=""):
        if self.active_table is None:
            print("No table selected. Use 'USE <table>' first.")
            return []

        try:
            options = self._parse_list_arguments(arguments)
            requested_columns = options["columns"]
            available_columns = self._active_table_columns()
            missing_columns = [
                column for column in requested_columns if column not in available_columns
            ]
            if missing_columns:
                print(
                    f"WARNING: Column(s) not found in '{self.active_table}': "
                    + ", ".join(missing_columns)
                )
                return []
            if options["order_by"] and options["order_by"][0] not in available_columns:
                print(
                    f"WARNING: Column '{options['order_by'][0]}' not found in "
                    f"'{self.active_table}'."
                )
                return []

            column_names = requested_columns or available_columns
            select_columns = ", ".join(_quote_identifier(column) for column in column_names)
            query = f"SELECT {select_columns} FROM {_quote_identifier(self.active_table)}"
            if options["where"]:
                query += f" WHERE {options['where']}"
            if options["order_by"]:
                column, direction = options["order_by"]
                query += f" ORDER BY {_quote_identifier(column)} {direction}"
            if options["limit"] is not None:
                query += f" LIMIT {options['limit']} OFFSET {options['offset']}"
            self._debug(query)
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            if not rows:
                print(f"No records found in '{self.active_table}'.")
                return []

            self._display_rows(column_names, rows)
            return rows
        except (ValueError, sqlite3.Error) as error:
            print(f"SQL Error: {error}")
            return []

    def cmd_find(self, condition):
        """Display the first active-table record matching a SQL condition."""

        if self.active_table is None:
            print("No table selected. Use 'USE <table>' first.")
            return None
        condition = (condition or "").strip()
        if condition.upper().startswith("FOR "):
            condition = condition[4:].strip()
        if condition.upper().startswith("WHERE "):
            condition = condition[6:].strip()
        if not condition:
            print("Missing condition. Use: FIND <condition> or LOCATE FOR <condition>")
            return None
        try:
            columns = self._active_table_columns()
            query = (
                f"SELECT {', '.join(_quote_identifier(column) for column in columns)} "
                f"FROM {_quote_identifier(self.active_table)} WHERE {condition} LIMIT 1"
            )
            self._debug(query)
            self.cursor.execute(query)
            row = self.cursor.fetchone()
            if row is None:
                print(f"No matching record found in '{self.active_table}'.")
                return None
            self._display_rows(columns, [row])
            return row
        except sqlite3.Error as error:
            print(f"SQL Error: {error}")
            return None

    def _parse_assignments(self, text, separator):
        columns = self._active_table_columns()
        assignments = []
        for item in _split_sql_items(text):
            if separator == "=":
                name, delimiter, value = item.partition("=")
                if not delimiter:
                    name, value = None, None
                else:
                    name, value = name.strip(), value.strip()
            else:
                name, value = _split_keyword(item, separator)
            if name is None or not name or not value:
                raise ValueError(f"Each assignment must use '<column> {separator} <value>'.")
            if name not in columns:
                raise ValueError(f"Column '{name}' does not exist in '{self.active_table}'.")
            assignments.append(f"{_quote_identifier(name)} = {value}")
        return assignments

    def _change_matching_records(self, assignments, condition):
        if not condition:
            print("A WHERE/FOR condition is required to avoid updating every record.")
            return False
        query = (
            f"UPDATE {_quote_identifier(self.active_table)} SET {', '.join(assignments)} "
            f"WHERE {condition}"
        )
        try:
            self._debug(query)
            self.cursor.execute(query)
            self.conn.commit()
            print(f"{self.cursor.rowcount} record(s) updated in '{self.active_table}'.")
            return True
        except sqlite3.Error as error:
            print(f"SQL Error: {error}")
            return False

    def cmd_update(self, arguments):
        """Run UPDATE SET ... WHERE ... against the active table."""

        if self.active_table is None:
            print("No table selected. Use 'USE <table>' first.")
            return False
        before_where, condition = _split_keyword(arguments or "", "WHERE")
        set_match = re.fullmatch(r"SET\s+(.+)", before_where or "", re.I | re.S)
        if before_where is None or set_match is None:
            print("Usage: UPDATE SET <column>=<value> [, ...] WHERE <condition>")
            return False
        try:
            assignments = self._parse_assignments(set_match.group(1).strip(), "=")
        except ValueError as error:
            print(f"Update error: {error}")
            return False
        return self._change_matching_records(assignments, condition)

    def cmd_replace(self, arguments):
        """Run dBASE-style REPLACE <column> WITH <value> FOR <condition>."""

        if self.active_table is None:
            print("No table selected. Use 'USE <table>' first.")
            return False
        assignments_text, condition = _split_keyword(arguments or "", "FOR")
        if assignments_text is None:
            print("Usage: REPLACE <column> WITH <value> [, ...] FOR <condition>")
            return False
        try:
            assignments = self._parse_assignments(assignments_text, "WITH")
        except ValueError as error:
            print(f"Replace error: {error}")
            return False
        return self._change_matching_records(assignments, condition)

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
        """Compatibility helper for SELECT, which is an alias for LIST."""

        return self.cmd_list(condition)

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
            self.cmd_list(args)
        elif base_command in {"FIND", "LOCATE"}:
            self.cmd_find(args)
        elif base_command == "UPDATE":
            self.cmd_update(args)
        elif base_command == "REPLACE":
            self.cmd_replace(args)
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
