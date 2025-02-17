import sqlite3
import os, csv, json
import xml.etree.ElementTree as ET


__version__ = "0.2.1" # 2025/02

HELP_TXT = """
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
"""



class Db3:
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
        "EXPO": "EXPORT"
    }

    def __init__(self, main_bb="main.sql"):
        self.db_file = main_bb
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self.active_table = None
        self.export_dir = "export"
        self.debug_mode = False
        os.makedirs(self.export_dir, exist_ok=True)
    
    def debug(self, mode: bool):
        self.debug_mode = mode
        print("Debug mode enabled." if mode else "Debug mode disabled.")

    def execute(self, query, params=(), suppress_debug=False):
        """Executes a SQL query while preventing duplicate debug messages."""
        print("-"*30)
        if self.debug_mode and not suppress_debug:
            print(f"DEBUG: Executing SQL → {query}")  # Only prints if suppress_debug=False
        
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"SQL Error: {e}")
            return None


    def run_script(self, filename):
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
                        self.execute_dbase_command(cmd)
                        print("-" * 30)  # Separator after each command
        except Exception as e:
            print(f"Error executing file: {e}")
    def cmd_use(self, table_name):
        """Sets the active table for operations."""
        if not table_name:
            print("Usage: USE <table_name>")
            return
        self.active_table = table_name
        print(f"Using table '{table_name}'.")

    def cmd_showx(self):
        """Lists all tables in the database."""
        tables = self.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        print("Tables:", [t[0] for t in tables] if tables else "No tables found.")
    
    def cmd_show(self):
        """Lists all tables in the database and highlights the active one."""
        tables = self.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        
        if not tables:
            print("No tables found.")
            return

        table_list = [t[0] for t in tables]

        # Highlight the active table if set
        print("Tables:")
        for table in table_list:
            if table == self.active_table:
                print(f" → {table}  (ACTIVE)")
            else:
                print(f"   {table}")

    def cmd_struct(self):
        """Displays the structure of the active table."""
        if self.active_table is None:
            print("No table selected. Use 'USE <table>' first.")
            return
        self.execute_dbase_command("STRUCT")

    def cmd_list(self):
        """Lists all rows in the active table."""
        if self.active_table is None:
            print("No table selected. Use 'USE <table>' first.")
            return
        self.execute_dbase_command("LIST")

    def export(self, table_name, filename, file_format):

        # Ověříme, zda existuje export_dir
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)
            if self.debug_mode:
                print(f"DEBUG: Created export directory → {self.export_dir}")
        
        # Sestavíme plnou cestu k výstupnímu souboru
        file_path = os.path.join(self.export_dir, filename)

        # SELECT * FROM table_name
        query = f"SELECT * FROM {table_name}"
        if self.debug_mode:
            print(f"DEBUG: Exporting table → {table_name}")
            print(f"DEBUG: Executing SQL → {query}")
        try:
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            column_names = [desc[0] for desc in self.cursor.description]
        except sqlite3.Error as e:
            print(f"SQL Error: {e}")
            return

        # Pokud v tabulce nejsou žádná data, jen varování
        if not rows:
            print(f"WARNING: No data found in '{table_name}', nothing to export.")
            return

        # Rozlišíme formát
        file_format = file_format.lower()
        if file_format == "csv":
            # Export do CSV
            try:
                with open(file_path, "w", newline='', encoding="utf-8") as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(column_names)  # hlavička
                    writer.writerows(rows)        # řádky
                print(f"SUCCESS: Data exported to '{file_path}' in CSV format.")
            except Exception as e:
                print(f"ERROR: Failed to export CSV → {e}")

        elif file_format == "json":
            # Export do JSON
            try:
                data = [dict(zip(column_names, row)) for row in rows]
                with open(file_path, "w", encoding="utf-8") as json_file:
                    json.dump(data, json_file, indent=4, ensure_ascii=False)
                print(f"SUCCESS: Data exported to '{file_path}' in JSON format.")
            except Exception as e:
                print(f"ERROR: Failed to export JSON → {e}")

        elif file_format == "xml":
            # Export do XML
            try:
                root = ET.Element("table", name=table_name)
                for row in rows:
                    row_elem = ET.SubElement(root, "row")
                    for col_name, value in zip(column_names, row):
                        col_elem = ET.SubElement(row_elem, col_name)
                        # převedeme None na prázdný text nebo rovnou ""
                        col_elem.text = "" if value is None else str(value)

                # Vygenerujeme výsledný XML řetězec
                xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")
                # Přidáme deklaraci
                xml_str = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_str
                # Pokud chcete mít každý <row> na nové řádce:
                xml_str = xml_str.replace("</row>", "</row>\n")

                with open(file_path, "w", encoding="utf-8") as xml_file:
                    xml_file.write(xml_str)

                print(f"SUCCESS: Data exported to '{file_path}' in XML format.")
            except Exception as e:
                print(f"ERROR: Failed to export XML → {e}")

        else:
            print(f"ERROR: Unsupported file format '{file_format}'. Use csv, json, or xml.")

    def export_active(self, filename):
        if not self.active_table:
            print("No active table selected.")
            return
        import os
        _, ext = os.path.splitext(filename.lower())
        if ext == ".csv":
            file_format = "csv"
        elif ext == ".xml":
            file_format = "xml"
        elif ext == ".json":
            file_format = "json"
        else:
            print("Unknown file extension – please use .csv, .xml or .json.")
            return
        
        # voláme původní export (tři argumenty)
        self.export(self.active_table, filename, file_format)


    def execute_dbase_command(self, command):
        words = command.strip().split(" ", 1)
        base_command = words[0].upper()
        args = words[1] if len(words) > 1 else ""
        
        base_command = self.COMMANDS.get(base_command, base_command)
        if base_command == "HELP":
            print(HELP_TXT)

        elif base_command == "DEBUG":
            if args.lower() == "true":
                self.debug(True)
            elif args.lower() == "false":
                self.debug(False)
            else:
                print("Usage: DEBUG true/false")

        elif base_command == "MODIF":
            params = args.split()
            if len(params) < 3:
                print("Usage: MODIF ADD <column_name> <column_type>")
                return
            action, column_name, column_type = params[0], params[1], params[2]
            if action.upper() == "ADD":
                self.execute(f"ALTER TABLE {self.active_table} ADD COLUMN {column_name} {column_type}")
                print(f"Column '{column_name}' added to '{self.active_table}'.")
            elif action.upper() == "DROP":
                print("Dropping columns is not natively supported in SQLite.")
            else:
                print("Invalid MODIF command.")

        elif base_command == "USE":
            self.active_table = args
            print(f"Using table '{args}'.")

        elif base_command == "LIST":
            if self.active_table is None:
                print("No table selected. Use 'USE <table>' first.")
                return

            try:
                if self.debug_mode:
                    print(f"DEBUG: Active table → {self.active_table}")  # Debug output
                query = f"SELECT * FROM {self.active_table}"
                if self.debug_mode:
                    print(f"DEBUG: Executing SQL → {query}")  # Debug output SQL

                rows = self.execute(query)

                if not rows:
                    print(f"No records found in '{self.active_table}'.")
                    return

                # Fetch column names
                self.cursor.execute(f"PRAGMA table_info({self.active_table})")
                column_names = [col[1] for col in self.cursor.fetchall()]

                # Print column headers
                if column_names:
                    print(" | ".join(column_names))
                    print("-" * (len(column_names) * 10))

                # Print row data
                for row in rows:
                    print(" | ".join(map(str, row)))

            except sqlite3.Error as e:
                print(f"SQL Error: {e}")

        elif base_command == "STRUCT":
            """Displays the structure of the active table."""
            if self.active_table is None:
                print("No table selected. Use 'USE <table>' first.")
                return
            
            try:
                self.cursor.execute(f"PRAGMA table_info({self.active_table})")
                columns = self.cursor.fetchall()
                
                if columns:
                    print(f"Structure of '{self.active_table}':")
                    print(f"{'Column':<20}{'Type':<10}{'Primary Key'}")
                    print("-" * 40)
                    
                    for col in columns:
                        print(f"{col[1]:<20}{col[2]:<10}{'YES' if col[5] else 'NO'}")
                else:
                    print(f"No columns found in '{self.active_table}'.")
            except sqlite3.Error as e:
                print(f"SQL Error: {e}")

        elif base_command == "DELETE":
            query = f"DELETE FROM {self.active_table} {args.strip()}"
            if self.debug_mode:
                print(f"DEBUG: Executing SQL → {query}")  # REMOVE THIS LINE
            self.execute(query)
            print(f"Records matching '{args.strip()}' deleted from '{self.active_table}'.")

        elif base_command == "SHOW":
            tables = self.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            print("Tables:", [t[0] for t in tables])

        elif base_command == "DROP":
            if self.debug_mode:
                print(f"DEBUG: Checking if table '{args}' exists")
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (args,))
            if not self.cursor.fetchone():
                print(f"Table '{args}' does not exist.")
                return
            confirm = input(f"Are you sure you want to drop table '{args}'? (Y/N): ").strip().upper()
            if confirm != "Y":
                print(f"Operation cancelled. Table '{args}' was not dropped.")
                return
            query = f"DROP TABLE {args}"
            if self.debug_mode:
                print(f"DEBUG: Executing SQL → {query}")
            self.execute(query)
            print(f"Table '{args}' dropped.")

        elif base_command == "CREATE":
            table_def = args.split(" ", 1)
            table_name = table_def[0]
            columns = table_def[1] if len(table_def) > 1 else "(id INTEGER PRIMARY KEY, data TEXT)"
            self.execute(f"CREATE TABLE {table_name} {columns}")
            print(f"Table '{table_name}' created.")

        elif base_command == "INSERT":
            #sql_query = f"INSERT INTO {self.active_table} {args.strip()}"
            sql_query = f"INSERT {args.strip()}" if args.strip().upper().startswith("INTO") else f"INSERT INTO {self.active_table} {args.strip()}"

            self.execute(sql_query)
        else:
            sql_query = f"{base_command} {args}"
            self.execute(sql_query)

    def close(self):
        self.conn.close()
        print("Database connection closed.")
