from lib.dbase3 import Db3, __version__

print("="*55)
print("dBase3 | lib.version:", __version__)

db = Db3("main2.db")
print("="*55)

#db.execute_dbase_command("DROP test2")
#db.create("test2", "(id INTEGER PRIMARY KEY, datum DATE, txt TEXT, num INTEGER)")
#db.cmd_show()

db.cmd_use("test2")
db.cmd_struct()
#db.execute_dbase_command('INSERT (txt,num) values ("Bob",123)')
#db.execute_dbase_command('INSERT (datum,txt,num) VALUES (date("now"), "Alice", 25)')
#db.execute_dbase_command('INSERT (datum,txt,num) VALUES ("2023-11-05", "Bob", 23)')
db.cmd_list()

db.select("ORDER BY txt")

#db.select('WHERE datum LIKE "2025%"')
data = db.select('WHERE datum LIKE "2025%" ORDER BY txt')

#print(data)
for line in data:
    print(line[2],line[3])