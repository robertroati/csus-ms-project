from perseus_lib import Library
from perseus_resource import Table, Service, Config
from pysqlcipher3 import dbapi2 as sqlite               
import json


KEY = "VGhpcyBzaG91bGQgYmUgcHJvdmlkZWQgYnk-GiOwIy0="        # FUTURE: server key management. 
DB_NAME = "/opt/perseus/perseus.db"


class Data:

    def __init__(self):
        conn = sqlite.connect(DB_NAME)                 # FUTURE: option to use database server. 
        conn.execute(f"PRAGMA key = '{KEY}'")

        # Create tables if they do not exist.
        create_tables = [
            'CREATE TABLE IF NOT EXISTS perseus_config (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT UNIQUE, value TEXT)',
            'CREATE TABLE IF NOT EXISTS perseus_operation (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, value TEXT, complete INTEGER)',
            'CREATE TABLE IF NOT EXISTS perseus_files (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT UNIQUE, is_monitored INTEGER)',
            'CREATE TABLE IF NOT EXISTS perseus_file_change (id INTEGER PRIMARY KEY AUTOINCREMENT, file_id INTEGER, file_hash TEXT, file_text TEXT, superceded_date TEXT)',
            'CREATE TABLE IF NOT EXISTS perseus_commands (id INTEGER PRIMARY KEY AUTOINCREMENT, command TEXT UNIQUE, is_monitored INTEGER)',
            'CREATE TABLE IF NOT EXISTS perseus_command_change (id INTEGER PRIMARY KEY AUTOINCREMENT, command_id INTEGER, command_hash TEXT, command_output TEXT, superceded_date TEXT)',
            'CREATE TABLE IF NOT EXISTS perseus_processes (id INTEGER PRIMARY KEY AUTOINCREMENT, command TEXT, cmdline TEXT UNIQUE, first_observed TEXT, last_observed TEXT, approved INTEGER)',
            'CREATE TABLE IF NOT EXISTS perseus_devices (id INTEGER PRIMARY KEY AUTOINCREMENT, device_name TEXT, device_type TEXT, first_observed TEXT, last_observed TEXT, approved INTEGER)',
            'CREATE TABLE IF NOT EXISTS perseus_log (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, value TEXT, date TEXT)',
        ]
        for t in create_tables:
            conn.execute(t)
        
        conn.close()



    def get_dbfilename(self):
        global DB_NAME
        return DB_NAME



    def load_configuration(self, config_filename):
        with open(config_filename, "r") as file:
            config = json.load(file)
        

        config_data = [
            (Config.SYSTEM_DEVICE_ID.value,         config['system']['device_id']),
            (Config.SYSTEM_CONSOLE_PW.value,        Library.getStrHash(config['system']['console_password'])),
            (Config.SYSTEM_CONSOLE_TIMEOUT.value,   str(config['system']['console_timeout'])),
            (Config.SYSTEM_UNLOCK_USER.value,       config['system']['unlock_username']),
            (Config.SYSTEM_UNLOCK_PW.value,         config['system']['unlock_password']),
            (Config.SYSTEM_USER_ACTIVITY_LOG.value, config['system']['user_activity_log']),
            (Config.SYSLOG_HOST.value,              config['syslog']['host']),
            (Config.SYSLOG_PORT.value,              str(config['syslog']['port'])),
            (Config.SFTP_HOST.value,                config['sftp']['host']),
            (Config.SFTP_PORT.value,                str(config['sftp']['port'])),
            (Config.SFTP_DIR.value,                 config['sftp']['remote_dir']),
            (Config.SFTP_USER.value,                config['sftp']['username']),
            (Config.SFTP_PW.value,                  config['sftp']['password']),
            (Config.SERVICE_PCAPS_ACTIVE.value,     str(config['service']['capture_pcaps'])),
            (Config.SERVICE_PCAP_INTERVAL.value,    str(config['service']['pcap_interval'])),
            (Config.SERVICE_PCAP_COUNT.value,       str(config['service']['maximum_pcaps'])),
            (Config.SERVICE_PCAP_INTERFACES.value,  config['service']['capture_interfaces']),
            (Config.SERVICE_HEARTBEAT_INTERVAL.value, str(config['service']['heartbeat_interval'])),
            (Config.SERVICE_COMMAND_INTERVAL.value, str(config['service']['command_check_interval'])),
            (Config.SERVICE_FILE_INTERVAL.value,    str(config['service']['file_check_interval'])),
            (Config.SERVICE_PROCESS_INTERVAL.value, str(config['service']['process_check_interval'])),
            (Config.SERVICE_DEVICE_INTERVAL.value,  str(config['service']['device_check_interval'])),
            (Config.CONTACT_NAME.value,             str(config['contact']['contact_name'])),
            (Config.CONTACT_EMAIL.value,            str(config['contact']['contact_email'])),
            (Config.CONTACT_PHONE.value,            str(config['contact']['contact_phone']))
        ]

        file_data = config['service']['files']
        command_data = config['service']['commands']

        self.insert_config_data(config_data)
        self.insert_command_list(command_data)
        self.insert_file_list(file_data)



    def get_config_value(self, configE):

        config_label = configE.value

        config_query = "SELECT value FROM perseus_config WHERE label = ?"

        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        cur.execute(config_query, (config_label,))
        row = cur.fetchone()
        value = row[0] if row else None
        
        conn.close()

        return value



    def update_console_password(self, new_password_hash):
        return self.update_config_by_label('console_pw', new_password_hash)



    def update_field_by_id(self, tablename, id, field, value):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        result = False
        try:
            cur.execute("UPDATE ? SET ? = ? WHERE id = ?", (tablename, field, value, id))
            if cur.rowcount == 0:
                print(f"No row found with id '{id}'.")
            else:
                result = True

            conn.commit()
        except sqlite.Error as e:
            print(f'Error occurred: {e}')
    
        conn.close()
        return result




    def update_config_by_label(self, label, value):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        result = False
        try:
            cur.execute("UPDATE perseus_config SET value = ? WHERE label = ?", (value,label))
            if cur.rowcount == 0:
                print(f"No row found with label '{label}'.")
            else:
                result = True

            conn.commit()

        except sqlite.Error as e:
            print(f'Error occurred: {e}')
    
        conn.close()
        return result


    def get_table(self, table_name, id = None):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        if table_name == 'perseus_file_change':
            query = f"SELECT fc.id, fc.file_id, f.filename, fc.file_hash, fc.superceded_date FROM perseus_file_change AS fc JOIN perseus_files AS f ON f.id = fc.file_id;"
        elif table_name == 'perseus_command_change':
            query = f"SELECT cc.id, cc.command_id, cmd.command, cc.command_hash, cc.superceded_date FROM perseus_command_change AS cc JOIN perseus_commands AS cmd ON cmd.id = cc.command_id;"
        else:
            query = f"SELECT * FROM {table_name}"

        if not id == None:
            query += f" WHERE id = {id}"

        cur.execute(query)

        column_names = [desc[0] for desc in cur.description]

        data = cur.fetchall()
        conn.close()

        return column_names, data
    

    def get_selection(self, table_name, id):
        return self.get_table(table_name, id)



    def print_table(self, table_name):
        print('\n')
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()

        # Don't print blobs.
        if table_name == 'perseus_file_change':
            query = f"SELECT fc.id, fc.file_id, f.filename, fc.file_hash, fc.superceded_date FROM perseus_file_change AS fc JOIN perseus_files AS f ON f.id = fc.file_id;"
        elif table_name == 'perseus_command_change':
            query = f"SELECT cc.id, cc.command_id, cmd.command, cc.command_hash, cc.superceded_date FROM perseus_command_change AS cc JOIN perseus_commands AS cmd ON cmd.id = cc.command_id;"
        else:
            query = f"SELECT * FROM {table_name}"

        cur.execute(query)

        column_names = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        # Determine maximum width for each column
        widths = [
            min(100,max(len(str(value)) for value in col)) for col in zip(column_names, *rows)
        ]

        # Print the headers
        header = " | ".join([name.ljust(width) for name, width in zip(column_names, widths)])
        print(header)
        print('-' * len(header))  # A line to separate headers and data

        print_count = 0
        for row in rows:
            # Mask Password
            row_list = list(row)
            if row_list[1] == 'console_pw':
                row_list[2] = '[Password Managed in Main Menu -> Configuration]'
            
            trunc_fields = [str(value)[:width] for value, width in zip(row_list, widths)]
            print(" | ".join([value.ljust(width) for value, width in zip(trunc_fields, widths)]))
            
            print_count += 1
            if print_count == 24:
                print("Press any key to continue...")
                Library.waitForKeypress()
                print_count = 0

        conn.close()



    def print_selection(self, table_name, id):
        print('\n')
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        query = f"SELECT * FROM {table_name} WHERE id = {id}"
        cur.execute(query)

        column_names = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        # Determine maximum width for each column
        widths = [
            min(100, max(len(str(value)) for value in col)) for col in zip(column_names, *rows)
        ]

        # Print headers
        header = " | ".join([name.ljust(width) for name, width in zip(column_names, widths)])
        print(header)
        # Separate Headers/Rows
        print('-' * len(header))

        # Print rows
        for row in rows:
            print(" | ".join([str(value).ljust(width) for value, width in zip(row, widths)]))

        conn.close()



    def insert_config_data(self, config_data):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        for c in config_data:
            try:
                conn.execute("INSERT INTO perseus_config (label, value) VALUES (?, ?)", (c[0], c[1]))
                conn.commit()
            except sqlite.IntegrityError:
                print(f"Duplicate config label '{c[0]}': already exists.")
                conn.rollback()
            except sqlite.OperationalError as e:
                print(f"Operational Error: {str(e)}")
                conn.rollback()

        conn.close()

    def get_file_list(self, monitored_only=False):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()

        query = 'SELECT * FROM perseus_files'
        if monitored_only:
            query += " WHERE is_monitored=1"

        cur.execute(query)
        rows = cur.fetchall()
        
        file_list = []
        for row in rows:
            file_list.append([row[0], row[1], row[2]])  # ID, Filename, is_monitored

        conn.close()

        return file_list



    def get_last_file_change(self, file_id):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        
        sql_query = "SELECT id, file_hash FROM perseus_file_change WHERE file_id=? ORDER BY id DESC LIMIT 1"
        cur.execute(sql_query, (file_id,))
        row = cur.fetchone()

        if row:
            return row[0], row[1] # ID, file_hash
        else:
            return None, None



    def update_file_change(self, file_id, file_hash, file_text, last_change_id=None):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()

        # Update Last Change with superceded date
        if last_change_id != None:
            query = "UPDATE perseus_file_change SET superceded_date=? WHERE id=?"
            cur.execute(query, (Library.datetime(), last_change_id))

        # Insert change record
        query = "INSERT INTO perseus_file_change (file_id, file_hash, file_text, superceded_date) VALUES (?, ?, ?, NULL)"
        cur.execute(query, (file_id, file_hash, file_text))

        conn.commit()
        conn.close()



    def get_cmd_list(self, monitored_only=False):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()

        query = 'SELECT * FROM perseus_commands'
        if monitored_only:
            query += " WHERE is_monitored=1"

        cur.execute(query)
        rows = cur.fetchall()
        
        cmd_list = []
        for row in rows:
            cmd_list.append([row[0], row[1], row[2]])  # ID, command, is_monitored

        conn.close()

        return cmd_list



    def get_last_cmd_change(self, command_id):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        
        query = "SELECT id, command_hash FROM perseus_command_change WHERE command_id=? ORDER BY id DESC LIMIT 1"
        cur.execute(query, (command_id,))
        row = cur.fetchone()

        if row:
            return row[0], row[1] # ID, command_hash
        else:
            return None, None



    def update_cmd_change(self, cmd_id, cmd_hash, cmd_text, last_change_id=None):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()

        # Update Last Change with superceded date
        if last_change_id != None:
            query = "UPDATE perseus_command_change SET superceded_date=? WHERE id=?"
            cur.execute(query, (Library.datetime(), last_change_id))

        # Insert change record
        query = "INSERT INTO perseus_command_change (command_id, command_hash, command_output, superceded_date) VALUES (?, ?, ?, NULL)"
        cur.execute(query, (cmd_id, cmd_hash, cmd_text))

        conn.commit()
        conn.close()



    def insert_file_list(self, file_list):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        result = False
        for f in file_list:
            try:
                conn.execute("INSERT INTO perseus_files (filename, is_monitored) VALUES (?,?)", (f, 1))
                conn.commit()
                result = True
            except sqlite.IntegrityError:
                print(f"Duplicate filename '{f}': file already exists.")
                conn.rollback()
            except sqlite.OperationalError as e:
                print(f"Operational Error: {str(e)}")
                conn.rollback()

        conn.close()
        return result 



    def insert_command_list(self, command_list):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        result = False
        for c in command_list:
            try:
                conn.execute("INSERT INTO perseus_commands (command, is_monitored) VALUES (?, ?)", (c, 1))
                conn.commit()
                result = True
            except sqlite.IntegrityError:
                print(f"Duplicate command '{c}': command already exists.")
                conn.rollback()
            except sqlite.OperationalError as e:
                print(f"Operational Error: {str(e)}")
                conn.rollback()
        return result



    def update_process_list(self, processes):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()

        current_time = Library.datetime()

        for process in processes:
            command = process[0]
            cmdline = process[1]

            # cmdline exists?
            cur.execute("SELECT * FROM perseus_processes WHERE cmdline = ?", (cmdline,))
            row = cur.fetchone()

            if row is None:
                # new cmdline
                cur.execute("INSERT INTO perseus_processes (command, cmdline, first_observed, last_observed, approved) VALUES (?, ?, ?, ?, ?)", (command, cmdline, current_time, current_time, 0))
            else:
                # Update last_observed if cmdline exists
                cur.execute("UPDATE perseus_processes SET last_observed = ? WHERE cmdline = ?", (current_time, cmdline))

            conn.commit()

        # Close the database connection
        conn.close()
        return True



    def update_device_list(self, devices):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()

        current_time = Library.datetime()

        for device in devices:
            dev_name = device[0]
            dev_type = device[1]

            # device exists?
            cur.execute("SELECT * FROM perseus_devices WHERE device_name = ? AND device_type = ?", (dev_name, dev_type))
            row = cur.fetchone()

            if row is None:
                # new device
                cur.execute("INSERT INTO perseus_devices (device_name, device_type, first_observed, last_observed, approved) VALUES (?, ?, ?, ?, ?)", (dev_name, dev_type, current_time, current_time, 0))
            else:
                # Update last_observed if cmdline exists
                cur.execute("UPDATE perseus_devices SET last_observed = ? WHERE device_name = ? AND device_type = ?", (current_time, dev_name, dev_type))

            conn.commit()

        # Close the database connection
        conn.close()
        return True



    def approve_all_processes(self):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        cur.execute("UPDATE perseus_processes SET approved = 1")
        conn.commit()
        conn.close()



    def approve_process_toggle(self, id):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        cur.execute("UPDATE perseus_processes SET approved = CASE WHEN approved = 1 THEN 0 ELSE 1 END WHERE id = ?", (id,))
        conn.commit()
        conn.close()



    def process_approval_status(self):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")

        cur = conn.cursor()
        cur.execute("SELECT * FROM perseus_processes WHERE approved = 0")
        
        # Fetch all the rows returned by the query
        rows = cur.fetchall()
        
        unapproved = []
        for row in rows:
            unapproved.append([row[1],row[2],row[4]]) # command, cmdline, last_observed

        conn.close()
        return unapproved

    def process_approved_list(self):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")

        cur = conn.cursor()
        cur.execute("SELECT * FROM perseus_processes WHERE approved = 1")
        
        # Fetch all the rows returned by the query
        rows = cur.fetchall()
        
        unapproved = []
        for row in rows:
            unapproved.append(row[2]) # cmdline

        conn.close()
        return unapproved




    def device_approval_status(self):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")

        cur = conn.cursor()
        cur.execute("SELECT * FROM perseus_devices WHERE approved = 0")
        
        # Fetch all the rows returned by the query
        rows = cur.fetchall()
        
        unapproved = []
        for row in rows:
            unapproved.append([row[1],row[2],row[4]]) # device_name, device_type, last_observed

        conn.close()
        return unapproved



    def device_approved_list(self):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")

        cur = conn.cursor()
        cur.execute("SELECT * FROM perseus_devices WHERE approved = 1")
        
        # Fetch all the rows returned by the query
        rows = cur.fetchall()
        
        unapproved = []
        for row in rows:
            unapproved.append([row[1],row[2]]) # device_name, device_type

        conn.close()
        return unapproved






    def approve_all_devices(self):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        cur.execute("UPDATE perseus_devices SET approved = 1")
        conn.commit()
        conn.close()



    def approve_device_toggle(self, id):
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        cur.execute("UPDATE perseus_devices SET approved = CASE WHEN approved = 1 THEN 0 ELSE 1 END WHERE id = ?", (id,))
        conn.commit()
        conn.close()



    def update_config(self, id, value):
        table_name = 'perseus_config'
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        update_sql = f"UPDATE {table_name} SET value = {value} WHERE id = {id}"
        result = False
        try:
            cur.execute(update_sql)
            conn.commit()
            conn.close()
            result = True
        except sqlite.IntegrityError:
            print(f"SQL Error.")
            conn.rollback()
        except sqlite.OperationalError as e:
            print(f"Operational Error: {str(e)}")
            conn.rollback()

        return result



    def update_files(self, id, value):
        table_name = 'perseus_files'
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        update_sql = f"UPDATE {table_name} SET is_monitored = {value} WHERE id = {id}"
        result = False
        try:
            cur.execute(update_sql)
            conn.commit()
            conn.close()
            result = True
        except sqlite.IntegrityError:
            print(f"SQL Error.")
            conn.rollback()
        except sqlite.OperationalError as e:
            print(f"Operational Error: {str(e)}")
            conn.rollback()

        return result



    def update_command(self, id, value):
        table_name = 'perseus_commands'
        conn = sqlite.connect(DB_NAME)
        conn.execute(f"PRAGMA key = '{KEY}'")
        cur = conn.cursor()
        update_sql = f"UPDATE {table_name} SET is_monitored = {value} WHERE id = {id}"
        result = False
        try:
            cur.execute(update_sql)
            conn.commit()
            conn.close()
            result = True
        except sqlite.IntegrityError:
            print(f"SQL Error.")
            conn.rollback()
        except sqlite.OperationalError as e:
            print(f"Operational Error: {str(e)}")
            conn.rollback()

        return result


