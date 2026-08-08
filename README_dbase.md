# pyDb Emulator

`pyDb Emulator` is a small, interactive database shell inspired by the
command-oriented workflow of dBASE III and later dBASE-family tools. It keeps
familiar short commands such as `CREA`, `INSE`, `DELE`, and `STRU`, while using
SQLite as its persistent storage engine.

It is not a binary `.dbf` reader and does not aim to be a complete dBASE
implementation. Think of it as a lightweight, dBASE-style front end to SQLite:
tables, rows, and column types are SQLite objects, while the prompt provides a
simple interactive workflow. The command interpreter itself lives in
`lib/wrapp_dbase3.py`; `py_dbase.py` is the configuration-aware command-line
entry point.

## Quick start

Python 3 is the only requirement. Start the default database with:

```bash
python py_dbase.py
```

This opens the configured default database and immediately displays the
`pyDb>` prompt:

```text
pyDb Emulator v0.4.0 (SQLite backend: ...\\data\\data.db)
pyDb> SHOW
No tables found.
pyDb> EXIT
```

At the prompt, type `HELP` to display the built-in command reference.

## Database files and tables

Database files and tables are separate concepts:

- A database file is one SQLite container, for example `data/data.db` or
  `data/projects.b`.
- A table is a named collection of rows inside that database file.
- One database file can contain any number of tables, for example `customers`,
  `orders`, and `products`.

For example, this creates two tables in the currently opened database:

```text
pyDb> CREATE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT)
pyDb> CREATE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL)
pyDb> SHOW
Tables in database:
- customers
- orders
```

The `USE` command selects one of those tables for commands that operate on the
current table, such as `LIST`, `INSERT`, `DELETE`, `STRUCT`, `MODIF`, and
`EXPORT`.

```text
pyDb> USE customers
pyDb> STRUCT
```

## Configuration

The project-root file [`py_dbase.json`](py_dbase.json) defines the default data
directory, database filename, and SQL debug setting:

```json
{
  "data_path": "./data",
  "default_database": "data.db",
  "debug": false
}
```

`data_path` is resolved relative to the directory containing `py_dbase.py`.
With the shipped settings, running without arguments opens
`data/data.db`. The directory is created automatically when necessary.
Executed SQL is hidden by default. Use `--debug` for diagnostic output, or
`--no-debug` to override a configuration that enables it.

## Startup options

### Select a database file

Use `--name` to choose a different database filename in the configured data
directory:

```bash
python py_dbase.py --name projects.db
```

This opens (or creates) `data/projects.db`; it does not change the default in
`py_dbase.json`. The argument is a filename only, so database files always stay
inside the configured data directory.

To list tables without opening the interactive prompt:

```bash
python py_dbase.py --list
python py_dbase.py --name projects.db --list
python py_dbase.py --list --format json
```

Short forms are available for the common command-line options:

```bash
python py_dbase.py -h          # help
python py_dbase.py -v          # version
python py_dbase.py -l          # list tables and exit
python py_dbase.py -l --json   # list tables as JSON and exit
python py_dbase.py -c tasks_base.json
python py_dbase.py --create tasks_base.json
```

`--list --format json` (or `--list --json`) writes only one JSON object to
standard output, for example `{"database":"projects.db","tables":["orders"]}`.
It is therefore suitable for scripts. The CLI exits with status `0` after a
successful operation, `1` for a startup/database error, and `2` for invalid
configuration or command-line arguments.

### Create a table from JSON

Use `--crea` to initialize a table from a JSON definition stored in the data
directory:

```bash
python py_dbase.py --crea tasks_base.json
```

For `data/tasks_base.json`, this opens the default database and creates the
table `tasks` if it does not already exist. The table name is read from the
JSON `table` property. If that property is absent, the JSON filename without
its extension is used as a backward-compatible fallback.

The definition must contain a non-empty `columns` list. Each entry needs a
`field` value, which becomes the SQLite column name. Fields are created as
`TEXT`, except `uid`, which is created as an `INTEGER PRIMARY KEY`. Other
metadata, including `name` and `width`, remains available for application use
but does not alter the SQLite schema.

```json
{
  "version": 1,
  "table": "tasks",
  "columns": [
    {"field": "uid", "name": "id", "width": 5},
    {"field": "project", "name": "project", "width": 20},
    {"field": "prompt", "name": "prompt", "width": 20}
  ]
}
```

Both startup options can be combined. This creates `tasks_base` in
`data/projects.db`:

```bash
python py_dbase.py --name projects.db --crea tasks_base.json
```

## Commands

| Command | Description |
| --- | --- |
| `CREATE <table>` | Creates a table with default `id` and `data` columns. |
| `CREATE <table> (<columns>)` | Creates a table with explicit SQLite column definitions. |
| `USE <table>` | Selects a table for commands that use the active table. |
| `SHOW` | Lists all tables in the current database file. |
| `LIST [<cols>] [WHERE …] [ORDER BY …] [LIMIT …]` | Displays filtered, ordered, or paged active-table rows. |
| `FIND <condition>` / `LOCATE FOR <condition>` | Displays the first matching active-table row. |
| `STRUCT` | Displays the active table's columns. |
| `INSERT (columns) VALUES (values)` | Adds a row to the active table. |
| `UPDATE SET <col>=<value> WHERE <condition>` | Changes fields in matching rows. |
| `REPLACE <col> WITH <value> FOR <condition>` | dBASE-style form of an update. |
| `DELETE WHERE <condition>` | Deletes rows from the active table. |
| `DROP <table>` | Removes a table after `Y/N` confirmation. |
| `MODIF ADD <column> <type>` | Adds a column to the active table. |
| `MODIF DROP <column>` | Removes a column from the active table. |
| `EXPORT <file>.csv/json/xml` | Exports active-table rows to `export/`. |
| `RUN <file>.dbs` | Runs dBASE-style commands from a `.dbs` script. |
| `HELP` | Shows the built-in help. |
| `EXIT` | Closes the prompt and database connection. |

The following traditional abbreviations are recognized: `CREA`, `INSE`,
`SELE`, `DELE`, `STRU`, `MODI`, and `EXPO`.

## Examples

### A simple contacts table

```text
pyDb> CREA contacts
pyDb> USE contacts
pyDb> INSE (data) VALUES ('Ada Lovelace')
pyDb> INSE (data) VALUES ('Grace Hopper')
pyDb> LIST
id | data
--------------------
1 | Ada Lovelace
2 | Grace Hopper
```

### A table with explicit SQLite types

```text
pyDb> CREATE products (id INTEGER PRIMARY KEY, name TEXT, price REAL, in_stock INTEGER)
pyDb> USE products
pyDb> INSERT (name, price, in_stock) VALUES ('Keyboard', 49.90, 1)
pyDb> INSERT (name, price, in_stock) VALUES ('Mouse', 19.50, 0)
pyDb> LIST
id | name | price | in_stock
----------------------------------------
1 | Keyboard | 49.9 | 1
2 | Mouse | 19.5 | 0
```

### Multiple tables in one database

```text
pyDb> CREATE categories (id INTEGER PRIMARY KEY, title TEXT)
pyDb> CREATE products (id INTEGER PRIMARY KEY, category_id INTEGER, name TEXT)
pyDb> SHOW
pyDb> USE categories
pyDb> INSERT (title) VALUES ('Hardware')
pyDb> USE products
pyDb> INSERT (category_id, name) VALUES (1, 'Keyboard')
```

Changing the active table does not switch database files; it only changes the
current table inside the already opened database.

### List only selected columns

Pass one or more column names to `LIST` to display only those columns:

```text
pyDb> USE products
pyDb> LIST name price
name | price
--------------------
Keyboard | 49.9
Mouse | 19.5
```

If a requested column does not exist, pyDb prints a warning and leaves the
database unchanged:

```text
pyDb> LIST name unknown_column
WARNING: Column(s) not found in 'products': unknown_column
```

### Filter, order, limit, and page rows

`LIST` accepts standard SQLite conditions and validates all selected and
ordering columns. `LIMIT` may use `OFFSET`; alternatively use one-based
`PAGE` with `SIZE`:

```text
pyDb> LIST name price WHERE in_stock=1 ORDER BY price DESC LIMIT 10 OFFSET 20
pyDb> LIST name price ORDER BY name PAGE 2 SIZE 25
```

The latter displays records 26–50 in name order. Do not combine `LIMIT` and
`PAGE` in a single command.

### Find and update records

`FIND` and `LOCATE FOR` display the first matching record. Updates require a
condition so an accidental command cannot modify the complete table:

```text
pyDb> FIND name='Mouse'
pyDb> LOCATE FOR price < 20
pyDb> UPDATE SET price=17.90 WHERE name='Mouse'
pyDb> REPLACE in_stock WITH 0 FOR name='Mouse'
```

### Add a column later

```text
pyDb> USE products
pyDb> MODIF ADD sku TEXT
pyDb> INSERT (category_id, name, sku) VALUES (1, 'Mouse', 'MOU-001')
pyDb> STRUCT
```

### Remove rows

```text
pyDb> USE products
pyDb> DELE WHERE in_stock=0
pyDb> LIST
```

Write the condition after `WHERE`; do not include `FROM <table>`, because the
active table is already known.

### Export a table

```text
pyDb> USE products
pyDb> EXPORT products.csv
pyDb> EXPORT products.json
pyDb> EXPORT products.xml
```

The resulting files are written under `export/`. A table must contain at least
one row to export.

### Run a repeatable script

Create `demo.dbs` with commands such as:

```text
CREA demo
USE demo
INSE (data) VALUES ('first row')
INSE (data) VALUES ('second row')
LIST
EXPORT demo.json
```

Then run it from the prompt:

```text
pyDb> RUN demo.dbs
```

The repository also includes `test1.dbs` as a small smoke-test script.

## Notes and limitations

- SQLite data types and SQL syntax are used for table definitions and
  conditions.
- Select a table with `USE <table>` before active-table operations.
- `DROP <table>` asks for confirmation because it permanently removes that
  table and its rows from the current database file.
- `--crea` is intentionally schema initialization, not a data import command.
  It uses `CREATE TABLE IF NOT EXISTS`, so an existing same-named table is
  left unchanged.
