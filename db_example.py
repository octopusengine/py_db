from lib.dbase3 import Db3, __version__

print("="*55)
print("dBase3 | lib.version:", __version__)

db = Db3("main.sql")

print("="*55)

db.cmd_show()
db.cmd_use("test")

# db.execute_dbase_command('INSERT (data,age) values ("Bob",567)')
db.cmd_list()