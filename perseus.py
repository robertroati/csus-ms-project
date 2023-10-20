import getpass
import hashlib
import os
import subprocess
import sys
import tty
import socket
import json
import termios
from perseus_data import Data as Data1
from perseus_lib import Library
from datetime import datetime
from perseus_resource import Table, Service


service_socket = '/tmp/perseus'
terminate_program = False
session = { 'session_id' : '0', 'auth': False }


def print_data(t, max_col_width=50):
    table_data = service_get_table(t)

    if not table_data == None:
        print_formatted_data(table_data, max_col_width)


def print_data_selection(t, id, max_col_width=50):
    select_data = service_get_selection(t, id)

    if not select_data == None:
        print_formatted_data(select_data, max_col_width)


def print_formatted_data(table_data, max_col_width):
    columns = table_data['columns']
    data = table_data['data']

    max_widths = [min(max(len(str(item[i])) for item in [columns] + data), max_col_width) for i in range(len(columns))]

    header_str = " | ".join([columns[i][:max_widths[i]].ljust(max_widths[i]) for i in range(len(columns))])
    print(header_str)
    print("-" * len(header_str))

    print_c = 0
    for row in data:
        row_str = " | ".join([str(row[i])[:max_widths[i]].ljust(max_widths[i]) for i in range(len(row))])
        print(row_str)

        print_c += 1
        if print_c == 24:
            ui_wait_for_keypress(True)
            print_c = 0

           
def getStrHash(text):
    if isinstance(text, str):
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    else:
        return None



####################
#   UI FUNCTIONS   #
####################


# Pause terminal on keypress (on most shells)
def ui_wait_for_keypress(any_key_message=False):
    if any_key_message:
        print("Press any key to continue.")

    try:
        if sys.platform == 'win32':
            msvcrt.getch()
        else:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                return True
    except KeyboardInterrupt:
        pass
        return False


# Clears terminal screen (on most shells)
def ui_clear_screen():
    os.system('clear')


# PARENT: None
# CHILDREN: None
def ui_login():

    failure_count = 0
    logged_in = False 

    admin_name, admin_email, admin_telephone = service_get_contact()

    while not logged_in and failure_count < 4:
        ui_clear_screen()

        print("Perseus Forensics Collection System\n\n")
        print("Local Administrator Contact Information:")
        print(f"     Name:  {admin_name}")
        print(f"    Email:  {admin_email}")
        print(f"Telephone:  {admin_telephone}\n\n")
        if failure_count == 0:
            print("")
        else:
            print("Invalid Password.")

        pw = getpass.getpass("Enter Console Password: ")
        pw_hash = getStrHash(pw)

        logged_in = service_login(pw_hash)
        if not logged_in:
            failure_count += 1

    return logged_in


# PARENT: None
# CHILDREN: ui_configuration(), ui_file_monitoring(), ui_command_monitoring(), ui_process_monitoring(),
#           ui_device_monitoring(), ui_perseus_service(), ui_upload_data(), ui_lockdown_system()
def ui_main_menu():
    while True:
        ui_clear_screen()

        print("Main Menu:")
        print("1) Configuration")           # showconfig, editconfig
        print("2) File Monitoring")         # showfiles, editfiles, showfilechanges
        print("3) Command Monitoring")      # showcommands, editcommands, showcommandchanges
        print("4) Process Monitoring")      # showprocesses, approveprocesses
        print("5) Device Monitoring")       # showdevices, approvedevices
        print("6) Perseus Service")         # connection status, shutdown
        print("7) Upload Data")             # upload
        print("L) Lockdown System")         # lockdown
        print("x) Exit")                    # exit

        goto = input("\nEnter your choice: ")
        goto = goto.strip()

        if goto == "1":
            ui_configuration()
        if goto == "2":
            ui_file_monitoring()
        if goto == "3":
            ui_command_monitoring()
        if goto == "4":
            ui_process_monitoring()
        if goto == "5":
            ui_device_monitoring()
        if goto == "6":
            ui_perseus_service()
        if goto == "7":
            ui_upload_data()
        if goto == "L":
            ui_lockdown_system()
        if goto == "x":
            ui_clear_screen()
            print("Exiting Perseus Console.\n")
            break


# PARENT: ui_main_menu()
# CHILDREN: ui_show_config(), ui_edit_config()
def ui_configuration():

    while True:
        ui_clear_screen()
        print("Configuration Menu:")
        print("1) Show Configuration")
        print("2) Edit Configuration")
        print("3) Change Console Password")
        print("x) Back to Main Menu") 

        goto = input("\nEnter your choice: ")
        goto = goto.strip()

        if goto == "1":
            ui_show_config()
        elif goto == "2":
            ui_edit_config()
        elif goto == "3":
            ui_change_console_password()
        elif goto == "x":
            break
        else:
            print(f"Did not understand input: [{goto}].")


# PARENT: ui_configuration()
# CHILDREN: None
def ui_show_config():
    ui_clear_screen()
    print_data(Table.CONFIG)
    ui_wait_for_keypress(True)


# PARENT: ui_edit_config()
# CHILDREN: None

def ui_edit_config_item(id):
 
    ui_clear_screen()
    print_data_selection(Table.CONFIG, id)
    command = input("Enter new value ('x' to go back): ")
    command = command.strip()

    if command != "x":
        if service_update_config(id, command):            # UPDATE
            print("\nUpdate successful.")
        else:
            print("\nUpdate failed.")
        
        ui_wait_for_keypress(True)


# PARENT: ui_configuration()
# CHILDREN: ui_edit_config_item()
def ui_edit_config():

    ui_clear_screen()

    while True:
        print_data(Table.CONFIG)
        print('')
        command = input("Enter selection ('x' to go back): ")
        command = command.strip()
        if command == "x":
            break
        elif command.isnumeric():
            id = int(command)
            ui_edit_config_item(id)
        else:
            print(f"Invalid command [{command}].")


# PARENT: ui_configuration()
# CHILDREN: None
def ui_change_console_password():

    pw1 = pw2 = ''

    while True:
        ui_clear_screen()

        print("Change Console Password\n")
        print("[enter blank passwords to exit]\n\n")
        pw1 = getpass.getpass("   Enter Console Password: ")
        pw2 = getpass.getpass("Re-Enter Console Password: ")

        if pw1 != pw2: 
            print("Passwords did not match.")
            ui_wait_for_keypress(True)
        else:
            break
        
    if pw1 != '':
        new_pw_hash = Library.getStrHash(pw1)

        if service_update_password(new_pw_hash):
            print("Password updated successfully.\n")
            ui_wait_for_keypress(True)
        else:
            print("Password updated failed.\n")
            ui_wait_for_keypress(True)


# PARENT: ui_main_menu()
# CHILDREN: ui_show_files(), ui_edit_files(), ui_show_file_changes()
def ui_file_monitoring():

    while True:
        ui_clear_screen()

        print("File Monitoring Menu:")
        print("1) Show Files")          
        print("2) Edit Files")              # showfiles, editfiles, showfilechanges
        print("3) Show File Changes")      
        print("x) Exit")                    # exit

        goto = input("\nEnter your choice: ")
        goto = goto.strip()

        if goto == "1":
            ui_show_files()
        if goto == "2":
            ui_edit_files()
        if goto == "3":
            ui_show_file_changes()
        if goto == "x":
            break


# PARENT: ui_file_monitoring()
# CHILDREN: None
def ui_show_files():
    ui_clear_screen()
    print_data(Table.FILES)
    ui_wait_for_keypress(True)


# PARENT: ui_edit_files()
# CHILDREN: ui_edit_files_toggle_item() 
def ui_edit_files_toggle_select():

    while True:
        ui_clear_screen()
        print_data(Table.FILES)
        print('')
        command = input("Enter id number to modify ('x' to go back): ")
        command = command.strip()

        if command == "x":
            break
        elif command.isnumeric():
            id = int(command)
            ui_edit_files_toggle_item(id)
        else:
            print("Invalid command.")


# PARENT: ui_edit_files_toggle_select()
# CHILDREN: None 
def ui_edit_files_toggle_item(id):
 
    while True:
        ui_clear_screen()
        print_data_selection(Table.FILES, id)
        print('')
        print("0) Disabled")
        print("1) Enabled")
        print("x) Back")
        command = input(f"Enter selection for [{id}]: ")
        command = command.strip()

        if command == "x":
            break
        elif (command == "0" or command == "1"):
            if service_update_monitor(Table.FILES, id, int(command)):
                print("\nUpdate successful.")
                ui_wait_for_keypress(True)
                break
            else:
                print("\nUpdate failed.")
                ui_wait_for_keypress(True)
        else:
            print("Invalid command.")


# PARENT: ui_edit_files()
# CHILDREN: None 
def ui_edit_files_add():

    while True:
        ui_clear_screen()

        print_data(Table.FILES)
        print('')
        command = input("Enter path of new file ('x' to go back): ")
        command = command.strip()

        if command == "x":
            break
        else:
            if service_insert_monitor(Table.FILES, command):
                print("\nUpdate successful.")
                ui_wait_for_keypress(True)
                break
            else:
                print("\nUpdate failed.")
                ui_wait_for_keypress(True)


# PARENT: ui_file_monitoring()
# CHILDREN: ui_edit_files_add(), ui_edit_files_toggle_select(), 
def ui_edit_files():

    while True:
        ui_clear_screen()
        print_data(Table.FILES)
        print('')
        print("1) Enable/Disable Monitoring")
        print("2) Add New to Monitor")
        print("x) Back")
        command = input("Enter selection: ")
        command = command.strip()

        if command == "x":
            break
        elif command == "1":
            ui_edit_files_toggle_select()
        elif command == "2":
            ui_edit_files_add()
        else:
            print("Invalid command.")


# PARENT: ui_file_monitoring()
# CHILDREN: None
def ui_show_file_changes():
    ui_clear_screen()
    print_data(Table.FILECHG)
    ui_wait_for_keypress(True)


# PARENT: ui_main_menu()
# CHILDREN: ui_show_commands(), ui_edit_commands(), ui_show_command_changes()
def ui_command_monitoring():
    while True:
        ui_clear_screen()

        print("Command Monitoring Menu:")
        print("1) Show Commands")       
        print("2) Edit Commands")       
        print("3) Show Command Changes")    # showcommands, editcommands, showcommandchanges
        print("x) Exit")                    # exit

        goto = input("\nEnter your choice: ")
        goto = goto.strip()

        if goto == "1":
            ui_show_commands()
        if goto == "2":
            ui_edit_commands()
        if goto == "3":
            ui_show_command_changes()
        if goto == "x":
            break


# PARENT: ui_command_monitoring()
# CHILDREN: None
def ui_show_commands():
    ui_clear_screen()
    print_data(Table.COMMANDS)
    ui_wait_for_keypress(True)


# PARENT: ui_command_monitoring()
# CHILDREN: ui_edit_commands_add(), ui_edit_commands_toggle_select()
def ui_edit_commands():
    ui_clear_screen()

    while True:
        print_data(Table.COMMANDS)
        print('')
        print("1) Enable/Disable Monitoring")
        print("2) Add New to Monitor")
        command = input("Enter selection ('x' to go back): ")

        command = command.strip()
        if command == "x":
            break

        elif command == "1":
            ui_edit_commands_toggle_select()

        elif command == "2":
            ui_edit_commands_add()

        else:
            print("Invalid command.")


# PARENT: ui_edit_commands()
# CHILDREN: None
def ui_edit_commands_add():

    while True:
        ui_clear_screen()

        print_data(Table.COMMANDS)
        print('')
        command = input("Enter new command string ('x' to go back): ")
        command = command.strip()

        if command == "x":
            break
        else:
            add = command
            if service_insert_monitor(Table.COMMANDS, add):
                print("\nUpdate successful.")
                ui_wait_for_keypress(True)
                break
            else:
                print("\nUpdate failed.")
                ui_wait_for_keypress(True)    


# PARENT: ui_edit_commands()
# CHILDREN: ui_edit_commands_toggle_item()
def ui_edit_commands_toggle_select():
    ui_clear_screen()

    while True:
        ui_clear_screen()
        print_data(Table.COMMANDS)
        print('')
        command = input("Enter id number to modify ('x' to go back): ")
        command = command.strip()

        if command == "x":
            break
        elif command.isnumeric():
            id = int(command)
            ui_edit_commands_toggle_item(id)
        else:
            print("Invalid command.")


# PARENT: ui_edit_commands_toggle_select()
# CHILDREN: None
def ui_edit_commands_toggle_item(id):

    while True:
        ui_clear_screen()
        print_data_selection(Table.COMMANDS, id)
        print('')
        print("0) Disabled")
        print("1) Enabled")
        print("x) Back")
        command = input(f"Enter selection for [{id}]: ")
        command = command.strip()

        if command == "x":
            break
        elif (command == "0" or command == "1"):
            if service_update_monitor(Table.COMMANDS, id, int(command)):
                print("\nUpdate successful.")
                ui_wait_for_keypress(True)
                break
            else:
                print("\nUpdate failed.")
                ui_wait_for_keypress(True)
        else:
            print("Invalid command.")


# PARENT: ui_command_monitoring()
# CHILDREN: None
def ui_show_command_changes():
    ui_clear_screen()
    print_data(Table.COMMANDCHG)
    ui_wait_for_keypress(True)


# PARENT: ui_main_menu()
# CHILDREN: 
def ui_process_monitoring():
    while True:
        ui_clear_screen()

        print("Process Monitoring Menu:")
        print("1) Show Processes")           
        print("2) Approve Processes")        
        print("x) Exit")                    

        goto = input("\nEnter your choice: ")
        goto = goto.strip()

        if goto == "1":
            ui_show_processes()
        if goto == "2":
            ui_approve_processes()
        if goto == "x":
            break


# PARENT: ui_process_monitoring()
# CHILDREN: None
def ui_show_processes():
    ui_clear_screen()
    print_data(Table.PROCESSES)
    ui_wait_for_keypress(True)


# PARENT: ui_process_monitoring()
# CHILDREN: None
def ui_approve_processes():
    ui_clear_screen()

    while True:
        print_data(Table.PROCESSES)
        print('')
        print("Enter an ID number to toggle approval or enter 'all' to approve all processes.")
        command = input("Enter selection ('x' to go back): ")
        command = command.strip()

        if command == "x":
            break
        elif command.isnumeric():
            service_approve_process_toggle(int(command))
        elif command == "all":
            service_approve_all_processes()
        else:
            input("Invalid Command. Press [ENTER] to continue.")


# PARENT: ui_main_menu()
# CHILDREN: 
def ui_device_monitoring():
    while True:
        ui_clear_screen()

        print("Device Monitoring Menu:")
        print("1) Show Devices")           
        print("2) Approve Devices")        
        print("x) Back")                    

        goto = input("\nEnter your choice: ")
        goto = goto.strip()

        if goto == "1":
            ui_show_devices()
        if goto == "2":
            ui_approve_devices()
        if goto == "x":
            break


# PARENT: ui_device_monitoring()
# CHILDREN: None
def ui_show_devices():
    ui_clear_screen()
    print_data(Table.DEVICES)
    ui_wait_for_keypress(True)


# PARENT: ui_device_monitoring()
# CHILDREN: None
def ui_approve_devices():
    ui_clear_screen()

    while True:
        print_data(Table.DEVICES)
        print('')
        print("Enter an ID number to toggle approval or enter 'all' to approve all devices.")
        command = input("Enter selection ('x' to go back): ")
        command = command.strip()

        if command == "x":
            break
        elif command.isnumeric():
            service_approve_device_toggle(int(command))
        elif command == "all":
            service_approve_all_devices()
        else:
            input("Invalid Command. Press [ENTER] to continue.")


# PARENT: ui_main_menu()
# CHILDREN: 
def ui_perseus_service():
    while True:
        ui_clear_screen()
        
        service_conn_status = "Not Connected"
        if service_connection():
            service_conn_status = "Connected"

        print("Perseus Service Menu:\n")
        print(f"Service Connection:  {service_conn_status}\n\n")
        print("s) Stop Service")        
        print("x) Exit")                   

        goto = input("\nEnter your choice: ")
        goto = goto.strip()

        if goto == "s":
            ui_stop_service()
        if goto == "x":
            break


# PARENT: ui_perseus_service()
# CHILDREN: None
def ui_start_service():
    ui_clear_screen()
    # start_service()
    print('')
    ui_wait_for_keypress(True)


# PARENT: ui_perseus_service()
# CHILDREN: None
def ui_stop_service():
    ui_clear_screen()
    resp = service_send_message(Service.SHUTDOWN)
    print(resp)
    ui_wait_for_keypress(True)


# PARENT: ui_main_menu()
# CHILDREN: 
def ui_upload_data():
    while True:
        ui_clear_screen()

        print("Upload Data Menu:")
        print("1) Upload Monitoring Database")     
        print("2) Upload Logs")                    
        print("3) Upload All")              
        print("x) Exit")                    

        goto = input("\nEnter your choice: ")
        goto = goto.strip()

        if goto == "1":
            ui_upload(True, False)
        if goto == "2":
            ui_upload(False, True)
        if goto == "3":
            ui_upload(True, True)
        if goto == "x":
            break


# PARENT: ui_upload_data()
# CHILDREN: None
def ui_upload(database = False, logs = False):
    ui_clear_screen()

    success = True

    if database and not logs:
        print("Sending Database via SFTP.")
        success = service_send_single(Service.UPLOAD_DB)

    if logs and not database:
        print("Sending Logs via SFTP.")
        success = service_send_single(Service.UPLOAD_LOGS)

    if logs and database:
        print("Sending Database and Logs via SFTP.")
        success = service_send_single(Service.UPLOAD_LOGS)

    if success:
        print("Upload successful.")
    else:
        print("Upload failed.")

    ui_wait_for_keypress(True)


# PARENT: ui_main_menu()
# CHILDREN: None
def ui_lockdown_system():
    while True:
        ui_clear_screen()

        print("Lockdown System?\n\n")
        print("Are you sure you want to lock down this system?\n") 
        print("YES) Lockdown System")
        print(" NO) Exit")

        goto = input("\nEnter your choice: ").lower()
        goto = goto.strip()

        if goto == "yes":
            ui_clear_screen()
            #service_send_lockdown()
            print("Locking Down System.")
            sys.exit(0)
        if goto == "no":
            break


# PARENT: service_get_sock()
# CHILDREN: None
def ui_timeout(sock = None):
    ui_clear_screen()
    service_close_sock(sock)
    print("Session timed out. Closing Perseus.")
    sys.exit(0)



def service_connection():
    reply = service_send_message(Service.CHECK)
    return (True if "OK" in reply else False)



def service_get_sock():
    global service_socket
    global session

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(service_socket)

        sock.send(session['session_id'].encode())     # Send session_id
        data = sock.recv(256).decode()                # auth response
        if 'OK' in data:
            session["auth"] = True
        else:
            session["auth"] = False

            if session['session_id'] != "0" and session['auth'] == False:
                ui_timeout(sock)    # Session timed out.

        return sock

    except socket.timeout:
        print("Connection attempt timed out.")

    except FileNotFoundError:
        print("Could not connect to service.")

    except Exception as e:
        print(f"An error occurred: {e}")

    return None



def service_close_sock(sock):
    if sock != None:
        sock.close()



def service_login(pw):

    success = False

    sock = service_get_sock()
    try:
        sock.sendall(str(Service.LOGIN).encode())       # Send login command
        sock.recv(32)                                   # Receive command OK
        sock.sendall(pw.encode())                       # Send hashed PW
        session_id = sock.recv(64).decode()             # Receive Session or failure
        if not 'FAILURE' in session_id:
            session["session_id"] = session_id
            session["auth"] = True
            success = True

    except Exception as e:
        print(e)

    service_close_sock(sock)
    return success



def service_update_password(pw_hash):

    sock = service_get_sock()
    try:
        cmd = str(Service.UPDATE_PW) 
        sock.sendall(cmd.encode())              # send command
        sock.recv(16)                           # receive ok
        sock.sendall(pw_hash.encode())          # send tablename
        sock.recv(16)                           # receive ok
        return True
    
    except socket.timeout:
        print("Connection attempt timed out.")

    except FileNotFoundError:
        print("Could not connect to service.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        service_close_sock(sock)

    return False



def service_insert_monitor(t, monitor_item):

    sock = service_get_sock()
    try:
        cmd = str(Service.INSERT_MONITOR)
        sock.sendall(cmd.encode())              # send command
        sock.recv(16)                           # receive ok
        sock.sendall(str(t).encode())          # send tablename
        sock.recv(16)                           # receive ok
        sock.sendall(monitor_item.encode())     # send new item
        result = sock.recv(64).decode()         # receive response

        if "OK" in result:
            return True

    except socket.timeout:
        print("Connection attempt timed out.")

    except FileNotFoundError:
        print("Could not connect to service.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        service_close_sock(sock)

    return False



def service_update_config(id, newvalue):

    sock = service_get_sock()
    try:
        sid = str(id).encode('utf-8')

        sock.sendall(str(Service.UPDATE_CONFIG).encode())       # send command
        sock.recv(16)                                           # receive ok
        sock.sendall(sid.ljust(16))                             # send id number
        sock.recv(16)                                           # receive ok
        sock.sendall(newvalue.encode())                         # send new value
        result = sock.recv(128).decode()                        # receive response

        if "OK" in result:
            service_close_sock(sock)
            return True

    except socket.timeout:
        print("Connection attempt timed out.")

    except FileNotFoundError:
        print("Could not connect to service.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        service_close_sock(sock)

    return False



def service_update_monitor(t, id, newvalue):

    sock = service_get_sock()
    try:
        sid = str(id).encode('utf-8')
        val =  str(newvalue).encode('utf-8')

        cmd = str(Service.UPDATE_MONITOR)
        sock.sendall(cmd.encode())              # send command
        sock.recv(16)                           # receive ok
        sock.sendall(str(t).encode())          # send tablename
        sock.recv(16)                           # receive ok
        sock.sendall(sid.ljust(16))             # send id number
        sock.recv(16)                           # receive ok
        sock.sendall(val.ljust(16))             # send id number
        result = sock.recv(64).decode()         # receive response

        if "OK" in result:
            return True

    except socket.timeout:
        print("Connection attempt timed out.")

    except FileNotFoundError:
        print("Could not connect to service.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        service_close_sock(sock)

    return False



def service_get_contact():

    sock = service_get_sock()
    try:
        cmd = str(Service.GET_CONTACT)
        sock.sendall(cmd.encode())              # send command
        serialized_data = sock.recv(1024)       # Receive json serialized contact data
        contact_dict = json.loads(serialized_data.decode('utf-8'))

        return contact_dict['n'], contact_dict['e'], contact_dict['p']

    except socket.timeout:
        print("Connection attempt timed out.")

    except FileNotFoundError:
        print("Could not connect to service.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        service_close_sock(sock)

    return '', '', ''


# Retrieves a config variable. Returns single string.
def service_get_config_value(configE):

    sock = service_get_sock()

    response = None

    try:
        cmd = str(Service.GET_CONFIG_VALUE)
        cfg = configE.value
        sock.sendall(cmd.encode())                  # send command
        if 'ERROR' not in sock.recv(32).decode():   # receive ok
            sock.sendall(cfg.encode())              # send config_name
            response = sock.recv(256).decode()      # receive return value

        return response

    except socket.timeout:
        print("Connection attempt timed out.")

    except FileNotFoundError:
        print("Could not connect to service.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        service_close_sock(sock)

    return response



def service_approve_device_toggle(id):

    sock = service_get_sock()
    try:
        sid = str(id).encode('utf-8')

        cmd = str(Service.APPROVE_DEVICE_TOGGLE)
        sock.sendall(cmd.encode())              # send command
        sock.recv(16)                           # receive ok
        sock.sendall(sid.ljust(16))             # send id number
        sock.recv(16)                           # receive ok

    except socket.timeout:
        print("Connection attempt timed out.")

    except FileNotFoundError:
        print("Could not connect to service.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        service_close_sock(sock)



def service_approve_all_devices():
    service_send_single(Service.APPROVE_ALL_DEVICES)



def service_approve_process_toggle(id):

    sock = service_get_sock()
    try:
        sid = str(id).encode('utf-8')

        cmd = str(Service.APPROVE_PROCESS_TOGGLE)
        sock.sendall(cmd.encode())              # send command
        sock.recv(16)                           # receive ok
        sock.sendall(sid.ljust(16))             # send id number
        sock.recv(16)                           # receive ok

    except socket.timeout:
        print("Connection attempt timed out.")

    except FileNotFoundError:
        print("Could not connect to service.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        service_close_sock(sock)



def service_approve_all_processes():
    service_send_single(Service.APPROVE_ALL_PROCESSES)



def service_get_selection(t, id):

    table_data = None

    sock = service_get_sock()
    try:
        sid = str(id).encode('utf-8')

        cmd = str(Service.GET_SELECTION)
        sock.sendall(cmd.encode())              # send command
        sock.recv(16)                           # receive ok
        sock.sendall(t.value.encode())          # send tablename
        sock.recv(16)                           # receive ok
        sock.sendall(sid.ljust(16))             # send id number

        # Receive selection data
        dl = int(sock.recv(16).strip())
        dr = 0

        payload = ''
        while dr < dl:
            c = sock.recv(min(1024, dl - dr))
            if not c:
                break
            payload += c.decode('utf-8')
            dr = len(payload)            

        table_data = json.loads(payload)

    except socket.timeout:
        print("Connection attempt timed out.")

    except FileNotFoundError:
        print("Could not connect to service.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        service_close_sock(sock)

    return table_data



def service_get_table(t):

    table_data = None

    sock = service_get_sock()
    try:
        cmd = str(Service.GET_DATA)
        tbl = t.value
        sock.sendall(cmd.encode())
        sock.recv(64)
        sock.sendall(tbl.encode())

        dl = int(sock.recv(16).strip())
        dr = 0

        payload = ''
        while dr < dl:
            c = sock.recv(min(1024, dl - dr))
            if not c:
                break
            payload += c.decode('utf-8')
            dr = len(payload)            

        table_data = json.loads(payload)

    except socket.timeout:
        print("Connection attempt timed out.")

    except FileNotFoundError:
        print("Could not connect to service.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        service_close_sock(sock)

    return table_data



def service_send_lockdown():
    service_send_message(Service.LOCKDOWN)



def service_send_command_list(serviceE, msg):

    sock = service_get_sock()
    try:
        cmd = str(serviceE)
        sock.sendall(cmd.encode())
        sock.recv(32)                                   # Try to receive OK
        
        for m in msg:
            sock.sendall(m.encode())
            data = sock.recv(256).decode()              # Try to receive OK
            if not "OK" in data:
                print(f'[Perseus Service] {data}')         
                return False

    except socket.timeout:
        response = ("Connection attempt timed out.")

    except FileNotFoundError:
        response = ("Could not connect to service.")

    except Exception as e:
        response = (f"An error occurred: {e}")

    finally:
        service_close_sock(sock)

    return False



def service_send_single(serviceE):

    sock = service_get_sock()
    try:
        cmd = str(serviceE)
        sock.sendall(cmd.encode())                  # Send service command
        data = sock.recv(256).decode()              # Try to receive OK
        if "OK" in data:
            return True
        else:
            print(f'[Perseus Service] {data}')         

    except socket.timeout:
        print("Connection attempt timed out.")

    except FileNotFoundError:
        print("Could not connect to service.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        service_close_sock(sock)

    return False



def service_send_message(srvEnum):

    response = "Bad Request."
    sock = service_get_sock()
    try:
        cmd = str(srvEnum)
        sock.sendall(cmd.encode())
        data = sock.recv(256)
        response = f'[Perseus Service] {data.decode()}'

    except socket.timeout:
        response = ("Connection attempt timed out.")

    except FileNotFoundError:
        response = ("Could not connect to service.")

    except Exception as e:
        response = (f"An error occurred: {e}")

    finally:
        service_close_sock(sock)

    return response



def run_console():

    # Try to set console window to 240 columns.
    try:
        subprocess.run(f"stty rows {24} cols {240}", shell=True)
    except Exception as e:
        print(f"An error occurred: {e}")

    # Start UI

    if ui_login():
        ui_main_menu()
    else:
        ui_clear_screen()
        print("Login Failed.")
        print("Exiting.")
        sys.exit(0)


if __name__ == "__main__":
    run_console()