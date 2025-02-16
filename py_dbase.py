import sqlite3
import os

__version__ = "0.1.3" # 2025/02

# Main database file (persistent storage)
DB_FILE = "main.sql"
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Default active table (None at start)
active_table = None


# Supported commands
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
    "MODI": "MODIF"
}

SQL_TRANSLATION = {
    "INSE": "INSERT",
    "SELE": "SELECT"
}

def normalize_command(command):
    """Converts command to uppercase and replaces short dBASE III commands with SQL equivalents."""
    words = command.strip().split(" ", 1)
    base_command = words[0].upper()
    translated_command = SQL_TRANSLATION.get(base_command, base_command)
    return translated_command + (" " + words[1] if len(words) > 1 else "")

def get_full_command(user_input):
    """Finds the matching command based on the first 3-4 characters."""
    key = user_input[:4].upper() if len(user_input) >= 4 else user_input[:3].upper()
    return COMMANDS.get(key, None)

def table_exists(table_name):
    """Checks if a table exists in the database."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def show_tables():
    """Lists all tables in the database (SHOW command)."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    if tables:
        print("Tables in database:")
        for table in tables:
            print(f"- {table[0]}")
    else:
        print("No tables found.")

def show_structure():
    """Displays the structure of the active table."""
    if active_table is None:
        print("No table selected. Use 'USE <table>' first.")
        return
    
    try:
        cursor.execute(f"PRAGMA table_info({active_table})")
        columns = cursor.fetchall()
        if columns:
            print(f"Structure of '{active_table}':")
            print(f"{'Column':<20}{'Type':<10}{'Primary Key'}")
            print("-" * 40)
            for col in columns:
                print(f"{col[1]:<20}{col[2]:<10}{'YES' if col[5] else 'NO'}")
        else:
            print(f"No columns found in '{active_table}'.")
    except sqlite3.Error as e:
        print(f"SQL Error: {e}")

def modify_table(action, column_name, column_type=None):
    """Modifies the structure of the active table (ADD or DROP COLUMN)."""
    if active_table is None:
        print("No table selected. Use 'USE <table>' first.")
        return
    
    try:
        if action.upper() == "ADD":
            if not column_name or not column_type:
                print("Usage: MODIF ADD <column_name> <column_type>")
                return
            cursor.execute(f"ALTER TABLE {active_table} ADD COLUMN {column_name} {column_type}")
            conn.commit()
            print(f"Column '{column_name}' added to '{active_table}'.")

        elif action.upper() == "DROP":
            cursor.execute(f"PRAGMA table_info({active_table})")
            columns = cursor.fetchall()
            existing_columns = [col[1] for col in columns]

            if column_name not in existing_columns:
                print(f"Column '{column_name}' does not exist in '{active_table}'.")
                return

            if len(existing_columns) <= 2:
                print("Cannot drop the last column (except primary key).")
                return

            new_columns = [col for col in existing_columns if col != column_name]
            columns_str = ", ".join(new_columns)
            
            cursor.execute(f"CREATE TABLE {active_table}_new AS SELECT {columns_str} FROM {active_table}")
            cursor.execute(f"DROP TABLE {active_table}")
            cursor.execute(f"ALTER TABLE {active_table}_new RENAME TO {active_table}")
            conn.commit()
            print(f"Column '{column_name}' removed from '{active_table}'.")

    except sqlite3.Error as e:
        print(f"SQL Error: {e}")


def execute_file(filename):
    """Executes dBASE III commands from a .dbs script file."""
    if not filename.lower().endswith(".dbs"):
        print("Error: Only .dbs script files are allowed.")
        return
    
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return
    
    try:
        with open(filename, "r", encoding="utf-8") as file:
            commands = file.readlines()
            for cmd in commands:
                cmd = cmd.strip()
                if cmd:
                    print(f"Executing: {cmd}")
                    execute_command(cmd)
    except Exception as e:
        print(f"Error executing file: {e}")


def execute_command(command):
    """Processes and executes a command."""
    global active_table
    command = normalize_command(command)
    words = command.strip().split(" ", 1)
    if not words:
        return True

    base_command = get_full_command(words[0])
    if not base_command:
        print(f"Unknown command: {words[0]}")
        return True

    try:
        if base_command == "X":
            print("x")

        elif base_command == "LIST":
            if active_table is None:
                print("No table selected. Use 'USE <table>' first.")
                return True
            try:
                print(f"DEBUG: Active table → {active_table}")  # Debug výstup
                query = f"SELECT * FROM {active_table}"
                print(f"DEBUG: Executing SQL → {query}")  # Debug výstup SQL
                cursor.execute(query)
                rows = cursor.fetchall()

                if not rows:
                    print(f"No records found in '{active_table}'.")
                    return

                # Získání názvů sloupců
                column_names = [desc[0] for desc in cursor.description] if cursor.description else []

                if column_names:
                    print(" | ".join(column_names))
                    print("-" * (len(column_names) * 10))

                for row in rows:
                    print(" | ".join(map(str, row)))

            except sqlite3.Error as e:
                print(f"SQL Error: {e}")

        elif base_command == "DELETE":
            if active_table is None:
                print("No table selected. Use 'USE <table>' first.")
                return True
            if len(words) < 2:
                print("Missing condition for DELETE. Use: DELETE WHERE <condition>")
                return True
            try:
                query = f"DELETE FROM {active_table} " + words[1]  # Oprava: Použití původního funkčního přístupu
                print(f"DEBUG: Executing SQL → {query}")  # Debug výstup
                cursor.execute(query)
                conn.commit()  # Uložíme změny do databáze
                print(f"Record(s) deleted from '{active_table}'.")
            except sqlite3.Error as e:
                print(f"SQL Error: {e}")

        elif base_command == "INSERT":
            if active_table is None:
                print("No table selected. Use 'USE <table>' first.")
                return True
            try:
                query = words[1]
        
                # Oprava: Pokud už začíná na "INTO <table>", odstraníme první výskyt
                expected_intro = f"INTO {active_table}".upper()
                if query.upper().startswith(expected_intro):
                    query = query[len(expected_intro):].strip()

                # Sestavení správného dotazu
                query = f"INSERT INTO {active_table} {query}"
                
                print(f"DEBUG: Executing SQL → {query}")  # Debug výstup
                cursor.execute(query)
                conn.commit()
                print(f"Record inserted into '{active_table}'.")
            except sqlite3.Error as e:
                print(f"SQL Error: {e}")

        elif base_command == "CREATE":
            if len(words) < 2:
                print("Table name is missing.")
                return True
            table_def = words[1].split(" ", 1)
            table_name = table_def[0]
            
            # Pokud nejsou specifikovány sloupce, vytvoří se základní tabulka
            columns = table_def[1] if len(table_def) > 1 else "(id INTEGER PRIMARY KEY, data TEXT)"
            
            try:
                query = f"CREATE TABLE {table_name} {columns}"
                print(f"DEBUG: Executing SQL → {query}")  # Debug výstup
                cursor.execute(query)
                conn.commit()
                active_table = table_name  # Automaticky nastavíme tabulku jako aktivní
                print(f"Table '{table_name}' created and set as active.")
            except sqlite3.Error as e:
                print(f"SQL Error: {e}")

        elif base_command == "DROP":
            if len(words) < 2:
                print("Table name is missing.")
                return True
            table_name = words[1]

            # Ověření, zda tabulka existuje
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                print(f"Table '{table_name}' does not exist.")
                return True

            # Potvrzení smazání
            confirm = input(f"Are you sure you want to drop table '{table_name}'? (Y/N): ").strip().upper()
            if confirm != "Y":
                print(f"Operation cancelled. Table '{table_name}' was not dropped.")
                return True

            try:
                query = f"DROP TABLE {table_name}"
                print(f"DEBUG: Executing SQL → {query}")  # Debug výstup
                cursor.execute(query)
                conn.commit()
                print(f"Table '{table_name}' dropped.")
            except sqlite3.Error as e:
                print(f"SQL Error: {e}")

        elif base_command == "USE":
            if len(words) < 2:
                print("Table name is missing.")
                return True
            table_name = words[1]
            if not table_exists(table_name):
                print(f"Table '{table_name}' does not exist.")
                return True
            active_table = table_name
            print(f"Using table '{active_table}'. (Active Table Set)")

        elif base_command == "STRUCT":
            show_structure()

        elif base_command == "MODIF":
            params = words[1].split() if len(words) > 1 else []
            if len(params) < 2:
                print("Usage: MODIF ADD <column_name> <column_type>")
            else:
                modify_table(params[0], params[1], params[2] if len(params) > 2 else None)

        elif base_command == "SHOW":
            show_tables()

        elif base_command == "EXIT":
            print("Exiting emulator...")
            return False
        
        elif base_command == "RUN":
            if len(words) < 2:
                print("Filename is missing.")
                return True
            execute_file(words[1])
        
        elif base_command == "HELP":
            print("""
-------------------
Available Commands:
-------------------
CREATE <table_name>    - Creates a new table in main.sql (id INTEGER PRIMARY KEY, data TEXT)
INSERT (columns) VALUES (values) - Inserts data into the active table
SELECT                 - Displays all records from the active table
DELETE WHERE <condition> - Deletes records from the active table
DROP <table_name>      - Drops (removes) a table from main.sql
LIST                   - Lists all records from the active table
USE <table>            - Sets the active table to use for other commands
SHOW                   - Lists all tables in the database
STRUCT                 - Displays the structure of the active table
MODIF ADD <col> <type> - Adds a new column to the active table
MODIF DROP <col>       - Removes a column from the active table
SQL "<query>"          - Executes raw SQL query
RUN <file>.dbs         - Executes dBASE III commands from a .dbs script file
HELP                   - Displays this help message
EXIT                   - Exits the emulator
""")

    except sqlite3.Error as e:
        print(f"SQL Error: {e}")

    return True

# Main loop
print("="*50)
print(f"pyDb Emulator v{__version__} (SQLite backend: {DB_FILE})")
print("Type 'HELP' for available commands or 'EXIT' to quit.")

while True:
    command = input("pyDb> ").strip()
    if not execute_command(command):
        break

# Close database connection
conn.close()
