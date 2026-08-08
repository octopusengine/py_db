"""Behaviour checks for the dBASE-style query and command-line additions."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import py_dbase
from lib.wrapp_dbase3 import Db3


class Db3CommandTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = Db3(
            os.path.join(self.directory.name, "commands.db"),
            export_dir=self.directory.name,
        )
        with redirect_stdout(io.StringIO()):
            self.database.create(
                "products", "(id INTEGER PRIMARY KEY, name TEXT, price REAL, in_stock INTEGER)"
            )
            for name, price, in_stock in (
                ("Keyboard", 49.9, 1),
                ("Mouse", 19.5, 1),
                ("Cable", 5, 0),
                ("LIMIT product", 99, 1),
            ):
                self.database.cmd_insert(
                    f"(name, price, in_stock) VALUES ('{name}', {price}, {in_stock})"
                )

    def tearDown(self):
        self.database.close()
        self.directory.cleanup()

    def test_list_filters_orders_limits_and_pages(self):
        with redirect_stdout(io.StringIO()):
            rows = self.database.cmd_list(
                "name price WHERE in_stock=1 ORDER BY price DESC LIMIT 1 OFFSET 0"
            )
            page = self.database.cmd_list("name ORDER BY price PAGE 2 SIZE 1")
            quoted_clause = self.database.cmd_list("name WHERE name='LIMIT product' LIMIT 1")

        self.assertEqual(rows, [("LIMIT product", 99.0)])
        self.assertEqual(page, [("Mouse",)])
        self.assertEqual(quoted_clause, [("LIMIT product",)])

    def test_find_and_locate_return_first_matching_record(self):
        with redirect_stdout(io.StringIO()):
            found = self.database.cmd_find("name='Mouse'")
            located = self.database.cmd_find("FOR price < 20")

        self.assertEqual(found, (2, "Mouse", 19.5, 1))
        self.assertEqual(located, (2, "Mouse", 19.5, 1))

    def test_update_and_replace_change_only_matching_rows(self):
        with redirect_stdout(io.StringIO()):
            self.assertTrue(self.database.cmd_update("SET price=17.9 WHERE name='Mouse'"))
            self.assertTrue(
                self.database.cmd_replace("in_stock WITH 0 FOR name='Mouse'")
            )
            self.assertFalse(self.database.cmd_update("SET price=1"))

        rows = self.database.execute(
            "SELECT price, in_stock FROM products WHERE name='Mouse'", suppress_debug=True
        )
        self.assertEqual(rows, [(17.9, 0)])


class CommandLineTests(unittest.TestCase):
    def test_create_accepts_a_sql_schema_script(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = os.path.join(directory, "py_dbase.json")
            script_path = os.path.join(directory, "schema.sql")
            db_path = os.path.join(directory, "cli.db")
            with open(config_path, "w", encoding="utf-8") as config_file:
                json.dump(
                    {"data_path": directory, "default_database": "cli.db", "debug": False},
                    config_file,
                )
            with open(script_path, "w", encoding="utf-8") as script_file:
                script_file.write(
                    "CREATE TABLE projects (id INTEGER PRIMARY KEY);\n"
                    "CREATE TABLE tasks (id INTEGER PRIMARY KEY, project_id INTEGER);\n"
                )

            output = io.StringIO()
            with (
                patch.object(py_dbase, "CONFIG_FILE", config_path),
                patch.object(sys, "argv", ["py_dbase.py", "--crea", "schema.sql", "--list"]),
                redirect_stdout(output),
            ):
                status = py_dbase.main()

            database = Db3(db_path, export_dir=directory)
            self.assertTrue(database.table_exists("projects"))
            self.assertTrue(database.table_exists("tasks"))
            database.close()
        self.assertEqual(status, 0)
        self.assertIn("SQL definition script executed.", output.getvalue())

    def test_json_schema_supports_constraints_defaults_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Db3(os.path.join(directory, "schema.db"), export_dir=directory)
            with redirect_stdout(io.StringIO()):
                database.create("projects", "(id INTEGER PRIMARY KEY)")
            definition_path = os.path.join(directory, "tasks_schema.json")
            with open(definition_path, "w", encoding="utf-8") as definition_file:
                json.dump(
                    {
                        "table": "tasks",
                        "columns": [
                            {"field": "uid", "description": "Technical key"},
                            {
                                "field": "project_id",
                                "type": "INTEGER",
                                "not_null": True,
                                "foreign_key": {"table": "projects", "field": "id"},
                                "description": "Owning project",
                            },
                            {
                                "field": "parent_id",
                                "type": "INTEGER",
                                "foreign_key": "projects(id)",
                            },
                            {
                                "field": "code",
                                "type": "VARCHAR(20)",
                                "not_null": True,
                                "default": "new",
                                "unique": True,
                                "description": "External code",
                            },
                            {"field": "active", "type": "BOOLEAN", "default": True},
                        ],
                    },
                    definition_file,
                )

            with redirect_stdout(io.StringIO()):
                py_dbase.create_table_from_definition(database, directory, "tasks_schema.json")

            columns = {row[1]: row for row in database.execute("PRAGMA table_info(tasks)")}
            self.assertEqual(columns["project_id"][2:5], ("INTEGER", 1, None))
            self.assertEqual(columns["code"][2:5], ("VARCHAR(20)", 1, "'new'"))
            self.assertEqual(columns["active"][4], "1")
            foreign_keys = database.execute("PRAGMA foreign_key_list(tasks)")
            self.assertEqual(
                {(key[2], key[3], key[4]) for key in foreign_keys},
                {("projects", "project_id", "id"), ("projects", "parent_id", "id")},
            )
            indexes = database.execute("PRAGMA index_list(tasks)")
            self.assertTrue(any(index[2] for index in indexes))
            database.close()

    def test_json_schema_rejects_unsafe_column_type(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Db3(os.path.join(directory, "schema.db"), export_dir=directory)
            definition_path = os.path.join(directory, "invalid_schema.json")
            with open(definition_path, "w", encoding="utf-8") as definition_file:
                json.dump(
                    {"table": "invalid", "columns": [{"field": "value", "type": "TEXT; DROP TABLE x"}]},
                    definition_file,
                )

            with self.assertRaisesRegex(ValueError, "type"):
                py_dbase.create_table_from_definition(database, directory, "invalid_schema.json")
            database.close()

    def test_list_json_is_machine_readable_and_returns_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = os.path.join(directory, "py_dbase.json")
            db_path = os.path.join(directory, "cli.db")
            with open(config_path, "w", encoding="utf-8") as config_file:
                json.dump(
                    {"data_path": directory, "default_database": "cli.db", "debug": True},
                    config_file,
                )
            database = Db3(db_path, export_dir=directory)
            with redirect_stdout(io.StringIO()):
                database.create("items")
            database.close()

            output = io.StringIO()
            with (
                patch.object(py_dbase, "CONFIG_FILE", config_path),
                patch.object(sys, "argv", ["py_dbase.py", "--list", "--json", "--no-debug"]),
                redirect_stdout(output),
            ):
                status = py_dbase.main()

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue()), {"database": "cli.db", "tables": ["items"]})

    def test_configuration_error_returns_two(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = os.path.join(directory, "py_dbase.json")
            with open(config_path, "w", encoding="utf-8") as config_file:
                config_file.write("{}")

            with (
                patch.object(py_dbase, "CONFIG_FILE", config_path),
                patch.object(sys, "argv", ["py_dbase.py", "--list"]),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(py_dbase.main(), 2)


if __name__ == "__main__":
    unittest.main()
