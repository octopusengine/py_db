# pyDb Emulator

🚀 **pyDb Emulator** is a simple **dBASE III emulator** powered by Python and **SQLite**.  
It allows you to create, modify, and manage tables using dBASE III-style commands.

---

## 📖 **How to Run**
1. Ensure you have **Python 3.x** and SQLite installed.
2. Clone the repository:
   ```bash
   git clone https://github.com/...
   cd pydb-emulator
   ```
3. Run the emulator:
   ```bash
   python py_dbase.py
   ```
4. Use interactive commands or run a `.dbs` script:
   ```plaintext
   pyDb> RUN test1.dbs
   ```

---

## 🔧 **Available Commands**
| Command                   | Description |
|---------------------------|---------------------------------------------|
| `CREATE <table>`          | Creates a table with a primary key `id`. |
| `INSERT (columns) VALUES (values)` | Inserts a record into the active table. |
| `SELECT`                  | Displays all records in the active table. |
| `DELETE WHERE <condition>` | Deletes a record matching the condition. |
| `DROP <table>`            | Deletes a table (requires `Y/N` confirmation). |
| `LIST`                    | Displays the contents of the active table. |
| `USE <table>`             | Sets the active table for further commands. |
| `SHOW`                    | Lists all tables in the database. |
| `STRUCT`                  | Displays the structure of the active table. |
| `MODIF ADD <column> <type>` | Adds a new column to the active table. |
| `RUN <file>.dbs`          | Executes a script containing dBASE III commands. |
| `HELP`                    | Displays the list of commands. |
| `EXIT`                    | Exits the emulator. |

---

## 📝 **Example `.dbs` File**
```plaintext
DROP emplo
CREA emplo
USE emplo
INSE INTO emplo (data) VALUES ('Alice')
INSE INTO emplo (data) VALUES ('Bob')
STRUCT
LIST
MODIF ADD age INTEGER
STRUCT
INSE INTO emplo (data,age) VALUES ('Charlie',21)
LIST
DELE WHERE id=2
LIST
```
📌 **Run the script:**  
```plaintext
pyDb> RUN test1.dbs
```

---

## 🛠 **Notes**
- `DELETE` should be used as `DELE WHERE ...` instead of `DELETE FROM <table> WHERE ...`.
- `LIST` operates only on the currently active table (`USE <table>` must be set first).
- `MODIF` currently supports only column addition (`MODIF ADD ...`).

---

## 🤝 **Contributors**
💡 **Author**: [Y3nD@]  
🔗 **GitHub**: [https://github.com/octopusengine]([https://github.com/your-username](https://github.com/octopusengine))

📌 **Pull requests are welcome!** Feel free to contribute and improve this project. 😊

