from lib.dbase3 import Db3

def main():
    db = Db3("main.sql")
    # Default debug mode off
    print("="*55)
    print("dBase3 Emulator - Type HELP for commands or EXIT to quit")
    
    while True:
        command = input("dBase> ").strip()
        if not command:
            continue
        
        cmd_parts = command.split(" ", 1)
        base_command = Db3.COMMANDS.get(cmd_parts[0].upper(), cmd_parts[0].upper())
        args = cmd_parts[1] if len(cmd_parts) > 1 else ""

        if base_command == "EXIT":
            print("Exiting emulator...")
            break
        
        elif base_command == "HELP":
            db.execute_dbase_command(command)

        elif base_command == "DEBUG":
            if args.lower() == "true":
                db.debug_mode = True
                print("Debug mode enabled.")
            elif args.lower() == "false":
                db.debug_mode = False
                print("Debug mode disabled.")
            else:
                print("Usage: DEBUG true/false")

        elif base_command == "CREATE":
            db.execute_dbase_command(command)

        elif base_command == "INSERT":
            db.execute_dbase_command(command)
            """
            table_args = args.split(" ", 2)
            if len(table_args) < 3:
                print("Usage: INSERT <table_name> <columns> <values>")
            else:
                db.insert(table_args[0], table_args[1], table_args[2])
            """
            
        elif base_command == "SELECT":
            db.select(args)

        elif base_command == "DELETE":
            db.execute_dbase_command(command)

        elif base_command == "DROP":
            db.execute_dbase_command(command)
                
        elif base_command == "USE":
            db.cmd_use(args)

        elif base_command == "SHOW":
            db.cmd_show()

        elif base_command == "EXPORT":
            filename = args.strip()
            if not filename:
                print("Usage: EXPORT <filename>.csv/xml/json")
                continue            
            db.export_active(filename)

        elif base_command == "RUN":
            db.run_script(args)

        elif base_command == "STRUCT":
            db.cmd_struct()

        elif base_command == "LIST":
            db.cmd_list()

        elif base_command == "MODIF":
            db.execute_dbase_command(command)

        else:
            print(f"Unknown command: {base_command}")

    db.close()

if __name__ == "__main__":
    main()
