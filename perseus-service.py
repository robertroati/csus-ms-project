import paramiko
from enum import Enum
from perseus_data import Data
from perseus_syslog import Syslog
from perseus_lib import Library
from perseus_resource import Table, Service, Config



# Create or check file hashes
# Log any changes
# Create or check command hashes
# Log any changes
# Allow uploads of perseus database to sftp server
# Lock down system if required. Unlock pw provided by config, sha256 hashed.

import os
import signal
import time
import threading
import socket
import datetime
import pcapy
import json

config_file = 'config.json'
server_socket = '/tmp/perseus'
terminate_program = False
graceful_shutdown = False
console_timeout = 180

TESTING = True

logger = None

sessions = {}

def console_service():
    global terminate_program
    global logger

    logger.infoprint("Starting Console Communications.")

    try:
        # Make sure the socket does not already exist
        os.unlink(server_socket)
    except FileNotFoundError:
        pass

    # Create a Unix domain socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        sock.bind(server_socket)
        sock.listen(1)

        while not terminate_program:
            conn, client_addr = sock.accept()
            try:
                console_connection(conn, client_addr)
            finally:
                conn.close()

    except Exception as e:
        logger.errorprint(f"An error occurred: {e}")
    finally:
        sock.close()
        os.unlink(server_socket)

    logger.infoprint("Closing Console Communications.")


def console_connection(conn, addr):

    global console_timeout
    global terminate_program
    global logger

    d = Data()
    console_timeout = int(d.get_config_value(Config.SYSTEM_CONSOLE_TIMEOUT))

    logger.infoprint(f"Console connected.")

    while not terminate_program:

        # Clean expired sessions
        service_expire_sessions()

        auth = False

        # Get session id, or check if socket is closed (None). 
        data = conn.recv(64)                                                    # Receive session_id
        if not data:
            logger.infoprint(f'Console closed connection.')
            break

        # Check if authenticated
        session_id = data.decode()

        if session_id in sessions: 
            sessions[session_id] = Library.setTimer(console_timeout)
            conn.sendall(str(Service.OK).encode())                              # Send session response
            auth = True
        else:
            conn.sendall(str(Service.ERROR).encode())
            auth = False

        # Get command from console
        data = conn.recv(64)                                                    # Receive command
        cmd = data.decode()

        print(cmd)      # DEBUG

        # Simple check to test console/service connection.
        if cmd == str(Service.CHECK):
            conn.sendall(str(Service.OK).encode())

        # Console command to retrieve database table.
        elif cmd == str(Service.GET_CONTACT):
            command_get_contact(conn)

        # Console command to retrieve database table.
        elif cmd == str(Service.LOGIN):
            command_login(conn)

        # Console had multiple login failures.
        elif cmd == str(Service.LOGIN_FAILURE):
            command_login_failure(conn)

        # Console had multiple login failures.
        elif cmd == str(Service.UPDATE_PW):
            command_update_password(conn)

        # Console had multiple login failures.
        elif cmd == str(Service.UPDATE_CONFIG):
            command_update_config(conn)

        # Console had multiple login failures.
        elif cmd == str(Service.UPDATE_MONITOR):
            command_update_monitor(conn)

        # Console had multiple login failures.
        elif cmd == str(Service.INSERT_MONITOR):
            command_insert_monitor(conn)

        # Console command to retrieve database table.
        elif cmd == str(Service.GET_CONFIG_VALUE) and auth == True:
            command_get_config_value(conn)

        # Console command to retrieve database table.
        elif cmd == str(Service.GET_DATA) and auth == True:
            command_get_data(conn)

        # Console command to retrieve database table.
        elif cmd == str(Service.GET_SELECTION) and auth == True:
            command_get_selection(conn)

        elif cmd == str(Service.APPROVE_DEVICE_TOGGLE) and auth == True:
            command_approve_device_toggle(conn)

        elif cmd == str(Service.APPROVE_ALL_DEVICES) and auth == True:
            command_approve_all_devices(conn)

        elif cmd == str(Service.APPROVE_PROCESS_TOGGLE) and auth == True:
            command_approve_all_devices(conn)

        elif cmd == str(Service.UPLOAD_DB) and auth == True:
            command_upload_db(conn)

        elif cmd == str(Service.UPLOAD_LOGS) and auth == True:
            command_upload_logs(conn)

        elif cmd == str(Service.UPLOAD_ALL) and auth == True:
            command_upload_all(conn)

        elif cmd == str(Service.LOCKDOWN) and auth == True:
            command_system_lockdown(conn)
            
        elif cmd == str(Service.SHUTDOWN) and auth == True:
            command_service_shutdown(conn)

        # Well, that didn't work out.
        else:
            logger.infoprint(f'Received unknown command: {cmd}')
            conn.sendall(str(Service.ERROR).encode())



def command_login(conn):
    d = Data()

    hashed_pw_stored = d.get_config_value(Config.SYSTEM_CONSOLE_PW)


    conn.sendall(str(Service.OK).encode())                          # Send OK
    hashed_pw_input = conn.recv(128).decode()                       # Received Hashed PW

    if hashed_pw_input == hashed_pw_stored:
        new_session_id = Library.get_session_id()
        sessions[new_session_id] = Library.setTimer(300)
        conn.sendall(new_session_id.encode())                       # Send session id
    else:
        conn.sendall(str(Service.LOGIN_FAILURE).encode())           # Send failure.


def command_upload_db(conn):
    if service_upload_to_sftp(True, False):
        conn.sendall(str(Service.OK).encode())      # Send OK
    else:
        conn.sendall(str(Service.ERROR).encode())   # Send Error


def command_upload_logs(conn):
    if service_upload_to_sftp(False, True):
        conn.sendall(str(Service.OK).encode())      # Send OK
    else:
        conn.sendall(str(Service.ERROR).encode())   # Send Error


def command_upload_all(conn):
    if service_upload_to_sftp(True, True):
        conn.sendall(str(Service.OK).encode())      # Send OK
    else:
        conn.sendall(str(Service.ERROR).encode())   # Send Error


def command_approve_device_toggle(conn):
    d = Data()
    conn.sendall(str(Service.OK).encode())      # Send OK
    dev_id = int(conn.recv(16).strip())         # Get Device ID
    d.approve_device_toggle(dev_id)                 
    conn.sendall(str(Service.OK).encode())      # Send OK


def command_approve_all_devices(conn):
    d = Data()
    d.approve_all_devices()
    conn.sendall(str(Service.OK).encode())      # Send OK


def command_approve_process_toggle(conn):
    d = Data()
    conn.sendall(str(Service.OK).encode())      # Send OK
    dev_id = int(conn.recv(16).strip())         # Get Device ID
    d.approve_device_toggle(dev_id)                 
    conn.sendall(str(Service.OK).encode())      # Send OK


def command_approve_all_processes(conn):
    d = Data()
    d.approve_all_processes()
    conn.sendall(str(Service.OK).encode())


def command_get_contact(conn):
    d = Data()

    name = d.get_config_value(Config.CONTACT_NAME)
    email = d.get_config_value(Config.CONTACT_EMAIL)
    phone = d.get_config_value(Config.CONTACT_PHONE)

    data = { 'n' : name, 'e' : email, 'p' : phone }
    serialized_contact = json.dumps(data).encode('utf-8')

    conn.sendall(serialized_contact)


def command_get_config_value(conn):

    print("HIT COMMAND_GET_CONFIG_VALUE(CON) -- ERRRRRRROR -- config_name not enum")
    d = Data()

    conn.sendall(str(Service.OK).encode())
    config_name = conn.recv(32).decode()            # Get config name from client
    cfg = d.get_config_value(config_name)           # pull from DB
    conn.sendall(cfg.encode())                      # send value


def command_get_data(conn):
    d = Data()

    conn.sendall(str(Service.OK).encode())
    table_name = conn.recv(32).decode()             # Get table name from client
    cols, data = d.get_table(table_name)            # Package Data
    payload = {'columns': cols, 'data': data}
    send_data = json.dumps(payload)
    dl = str(len(send_data)).encode('utf-8')        # Tell Client payload size
    conn.sendall(dl.ljust(16))

    for i in range(0, len(send_data), 1024):        # Send client payload
        c = send_data[i:i+1024]
        conn.sendall(c.encode('utf-8'))



def command_get_selection(conn):
    d = Data()

    conn.sendall(str(Service.OK).encode())
    table_name = conn.recv(64).decode()             # Get table name from client
    conn.sendall(str(Service.OK).encode())
    selection_id = int(conn.recv(16).strip())       # Get selection id

    cols, data = d.get_selection(table_name, selection_id) # Package Data
    payload = {'columns': cols, 'data': data}
    send_data = json.dumps(payload)

    dl = str(len(send_data)).encode('utf-8')        # Tell Client payload size
    conn.sendall(dl.ljust(16))

    for i in range(0, len(send_data), 1024):        # Send client payload
        c = send_data[i:i+1024]
        conn.sendall(c.encode('utf-8'))


# Console command to intiatate system lockdown. 
def command_system_lockdown(conn):
    conn.sendall(str(Service.OK).encode())
    logger.criticalprint("Initiating System Lockdown.")
    system_lockdown()


# Shutdown service via console.
def command_service_shutdown(conn):
    global terminate_program

    conn.sendall(str(Service.OK).encode())
    logger.warningprint("Initiating Shutdown of Perseus.")
    terminate_program = True


def command_update_password(conn):
    conn.sendall(str(Service.OK).encode())      # Send command ok response
    new_pw_hash = conn.recv(256).decode()       # Receive new PW
    d = Data()
    result = d.update_console_password(new_pw_hash)

    if result:
        conn.sendall(str(Service.OK).encode())      # Send command ok response
    else:
        conn.sendall(str(Service.ERROR).encode())   # Send command ok response


def command_update_monitor(conn):
    d = Data()

    conn.sendall(str(Service.OK).encode())      # Send command ok response
    tbl = conn.recv(256).decode()               # Receive type (Command/File)
    conn.sendall(str(Service.OK).encode())      # Send command ok response
    selection_id = int(conn.recv(16).strip())   # Get selection id
    conn.sendall(str(Service.OK).encode())      # Send command ok response
    set_value = int(conn.recv(16).strip())      # Get new value

    result = False

    if "COMMAND" in tbl:
        result = d.update_command(selection_id, set_value)

    if "FILE" in tbl:
        result = d.update_files(selection_id, set_value)

    if result:
        conn.sendall(str(Service.OK).encode())      # Send command ok response
    else:
        conn.sendall(str(Service.ERROR).encode())      # Send command ok response


def command_insert_monitor(conn):
    d = Data()

    conn.sendall(str(Service.OK).encode())      # Send command ok response
    tbl = conn.recv(256).decode()               # Receive type (Command/File)
    conn.sendall(str(Service.OK).encode())      # Send command ok response
    new_monitor = conn.recv(1024).decode()      # Get new monitor item

    l = []
    l.append(new_monitor)


    result = False

    if "COMMAND" in tbl:
        result = d.insert_command_list(l)

    if "FILE" in tbl:
        result = d.insert_file_list(l)

    if result:
        conn.sendall(str(Service.OK).encode())      # Send command ok response
    else:
        conn.sendall(str(Service.ERROR).encode())      # Send command ok response



def command_update_config(conn):
    conn.sendall(str(Service.OK).encode())      # Send command ok response
    selection_id = int(conn.recv(16).strip())   # Get selection id
    conn.sendall(str(Service.OK).encode())      # Send command ok response
    config_value = conn.recv(1024).decode()     # Receive new value

    d = Data()
    result = d.update_config(selection_id, config_value)
    if result:
        conn.sendall(str(Service.OK).encode())      # Send command ok response
    else:
        conn.sendall(str(Service.ERROR).encode())   # Send command ok response



# Log Console login failure (prevents need for logger on console).
def command_login_failure(conn):
    conn.sendall(str(Service.OK).encode())
    logger.warningprint("Console login failure.")



def service_expire_sessions():
    global sessions

    expired = []
    for id, expires in sessions.items():
        if Library.isExpired(expires):
            expired.append(id)

    for id in expired:
        del sessions[id]



def service_upload_to_sftp(db = False, logs = False):
    d = Data()

    file_list = []

    if db:
        file_list.append( d.get_dbfilename() )
    if logs:
        file_list.append( d.get_config_value(Config.SYSTEM_USER_ACTIVITY_LOG))

    if file_list == []:
        return True

    host = d.get_config_value(Config.SFTP_HOST)
    port = d.get_config_value(Config.SFTP_PORT)
    username = d.get_config_value(Config.SFTP_USER)
    password = d.get_config_value(Config.SFTP_PW)
    directory = d.get_config_value(Config.SFTP_DIR)

    dt = datetime.now().strftime("%Y%m%d")
 
    # Create an SSH client
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Connect to the server
    ssh_client.connect(host, port, username, password)
    transport = ssh_client.get_transport()
    transport._preferred_ciphers = ('aes256-ctr', 'aes192-ctr', 'aes128-ctr')

    try:
        sftp = ssh_client.open_sftp()
        for f in file_list:
            src = f
            dest = dt + "_" + src
 
            logger.logprint(f"Uploading [{src}] to [{dest}].")
            sftp.put(src, dest)
 
        sftp.close()
        ssh_client.close()
        logger.logprint(f"Upload to [{host}] was successful.")
        return True
    
    except Exception as e:
        logger.errorprint(f"Upload failed with error: {e}")

    return False



def system_service():
    global terminate_program
    global logger

    logger.infoprint("Starting Perseus Service.")

    d = Data()

    td_process_list = int(d.get_config_value(Config.SERVICE_PROCESS_INTERVAL))
    td_device_list = int(d.get_config_value(Config.SERVICE_DEVICE_INTERVAL))
    td_file_hash_check = int(d.get_config_value(Config.SERVICE_FILE_INTERVAL))
    td_command_hash_check = int(d.get_config_value(Config.SERVICE_COMMAND_INTERVAL))
    td_heartbeat = int(d.get_config_value(Config.SERVICE_HEARTBEAT_INTERVAL))

    t_process_list = datetime.datetime.now()
    t_device_list = datetime.datetime.now()
    t_file_hash_check = datetime.datetime.now()
    t_command_hash_check = datetime.datetime.now()
    t_heartbeat = datetime.datetime.now()

    while not terminate_program:

        # Check file hashes
        if Library.isExpired(t_file_hash_check):

            t_file_hash_check = Library.setTimer(td_file_hash_check)

            file_list = d.get_file_list()
            for f in file_list:                 
                file_id = f[0]
                filename = f[1]
                is_monitored = f[2]

                if is_monitored:
                    current_file_hash = Library.getFileHash(filename)
                    last_change_id, last_file_hash = d.get_last_file_change(file_id)

                    if (current_file_hash != last_file_hash):
                        try:
                            with open(filename, 'r') as file:
                                file_text = file.read()

                            d.update_file_change(file_id,current_file_hash, file_text, last_change_id)
                            if last_change_id != None:
                                logger.warningprint(f"File '{filename}' has been changed.")
                            else:
                                logger.infoprint(f"File '{filename}' has been added.")

                        except FileNotFoundError:
                            logger.errorprint(f"The file '{filename}' was not found.")
                        except Exception as e:
                            logger.errorprint(f"A file read ({filename}) error occurred: {e}")


        # Check command hashes
        if Library.isExpired(t_command_hash_check):

            t_command_hash_check = Library.setTimer(td_command_hash_check)

            command_list = d.get_cmd_list()
            for c in command_list:  
                command_id = c[0]
                command_text = c[1]
                is_monitored = c[2]

                if is_monitored:

                    # Check for piped commands
                    cmd_output = Library.getCommandOutput(command_text)

                    current_cmd_hash = Library.getStrHash(cmd_output)
                    last_change_cmd_id, last_cmd_hash = d.get_last_cmd_change(command_id)

                    if (current_cmd_hash != last_cmd_hash):
                        d.update_cmd_change(command_id, current_cmd_hash, cmd_output, last_change_cmd_id)
                        if last_change_cmd_id != None:
                            logger.warningprint(f"Command Output '{command_text}' has changed.")
                        else:
                            logger.infoprint(f"Command Output '{command_text}' has been added.")



        # Running Process List
        if Library.isExpired(t_process_list):
            process_list = Library.getProcessInfo()
            d.update_process_list(process_list)
            notapproved = d.process_approval_status()

            if len(notapproved) != 0:
                for na in notapproved:
                    logger.warning(f"Unapproved process '{na[0]}', last observed '{na[2]}' with commandline '{na[1]}'.")

            t_process_list = Library.setTimer(td_process_list)

        # Connected Devices List
        if Library.isExpired(t_device_list):
            device_list = Library.getDeviceInfo()
            d.update_device_list(device_list)
            notapproved = d.device_approval_status()

            if len(notapproved) != 0:
                for na in notapproved:
                    logger.warning(f"Unapproved device '{na[0]}' of type '{na[1]}', last observed '{na[2]}'.")

            t_device_list = Library.setTimer(td_device_list)

        # Heartbeat
        if Library.isExpired(t_heartbeat):
            logger.infoprint("Perseus is running.")
            t_heartbeat = Library.setTimer(td_heartbeat)


        time.sleep(1)
    logger.infoprint("Closing Service.")



def pcap(interface, interval, max_pcaps):
    global terminate_program
    global logger

    pcap_path = f"pcaps/{interface}"
    os.makedirs(pcap_path, exist_ok=True)

    logger.infoprint(f"Capturing up to ({max_pcaps}) {interval}-second PCAPs for interface '{interface}' to directory '{pcap_path}'.")

    pcap_number = 0
    pcap_prefix = f"{pcap_path}/{Library.date()}_"
    pcap_suffix = f".pcap"

    # Prevent overwrite from restart
    while os.path.exists(pcap_prefix + str(pcap_number) + pcap_suffix):
        pcap_number += 1

    pc = pcapy.open_live(interface, 65536, 1, 100)
    while not terminate_program:

        df = pc.dump_open(f"{pcap_path}/{Library.date()}_{pcap_number}.pcap")

        capture_timer = Library.setTimer(interval)
        while (not Library.isExpired(capture_timer)) and (not terminate_program):
            (header, packet) = pc.next()
            df.dump(header, packet)

        df.close()
        
        # Iterate pcap file number
        pcap_number += 1

        # Clean up older files that are not within max_pcaps
        pcap_files = [f for f in os.listdir(pcap_path) if os.path.isfile(os.path.join(pcap_path, f)) and f.endswith('.pcap')]
        sorted_pcap_files = sorted(pcap_files, key=lambda x: os.path.getmtime(os.path.join(pcap_path, x)))
        remove_pcap_files = sorted_pcap_files[:-max_pcaps]

        for f in remove_pcap_files:
            os.remove(os.path.join(pcap_path, f))

    logger.infoprint(f"Closing PCAP capture of '{interface}'.")



def initialize_logger():
    global logger
    d = Data()
    sys_host = d.get_config_value(Config.SYSLOG_HOST)
    sys_port = int(d.get_config_value(Config.SYSLOG_PORT))
    logger = Syslog(sys_host, sys_port)



def load_configuration():
    d = Data()
    d.load_configuration(config_file)



def initiate_shell_logging():
    d = Data()
    ual = d.get_config_value(Config.SYSTEM_USER_ACTIVITY_LOG)

    # If user logging isn't in /etc/profile, add it to /etc/profile to capture shell commands. 
    if not Library.checkFileForString('/etc/profile', "PERSEUS"):
        print("Word Not Found")
        profile_str =   f"\n\n# PERSEUS User Activity Logging\n" \
                        f"export PROMPT_COMMAND='echo \"$(date \"+%Y-%m-%d %H:%M:%S\") $(whoami) [$$]: $(history 1 | sed \"s/^[ ]*[0-9]\+[ ]*//\")\" >> {ual}'\n"

        with open("/etc/profile", "a") as f:
            f.write(profile_str)

        with open(ual, "w") as f:
            pass

        os.chmod(ual, 0o1733)


#  System Lockdown: 
#     Create a new user *
#     Lock accounts *
#     Kill shell sessions *
#     Kill non-approved processes
#     Detach non-approved devices
#     Copy and store data
#     Upload all data
#     Disble network interfaces

def system_lockdown():
    global TESTING
    d = Data()

    if not TESTING:
        user = d.get_config_value(Config.SYSTEM_UNLOCK_USER)
        pw = d.get_config_value(Config.SYSTEM_UNLOCK_PW)

        # If creating the user failed, do not lock accounts.
        if Library.createUser(user, pw):
            locked_accounts = []
            lock_exception_list = [user]
            locked_accounts = Library.lockUserAccounts(lock_exception_list)
            logger.criticalprint(f"Locked Accounts: {locked_accounts}")
        else:
            logger.criticalprint(f"Failed to create special user {user}.")

        if not Library.createMOTD(user):
            logger.errorprint(f"Failed to create custom MOTD for user {user}.")

        terminated_user_sessions = Library.terminateUserSessions()
        logger.criticalprint(f"Terminated user sesssions: {terminated_user_sessions}")

#     Kill non-approved processes

#     Detach non-approved devices

#     Copy and store data

#     Upload all data

#     Disble network interfaces
        Library.disableEthInterfaces()



def service_stop():
    global logger
    global terminate_program
    global graceful_shutdown

    logger.warningprint("Service is shutting down.")

    terminate_program = True
    while not graceful_shutdown:
        time.sleep(1)



def main():
    global graceful_shutdown

    # Service is being stopped.
    signal.signal(signal.SIGTERM, service_stop)

    if os.path.exists(config_file):
        print("Importing Configuration file.")
        load_configuration()
        # Delete config file after import
        try:
            # os.remove(config_file)                        #  REMOVE COMMENT AFTER TESTING
            print(f"File {config_file} deleted successfully")
        except FileNotFoundError:
            print(f"File {config_file} not found")
        except PermissionError:
            print(f"Permission denied. Cannot delete {config_file}.")
        except Exception as e:
            print(f"An error occurred: {e}")


    initialize_logger()
    initiate_shell_logging()

    # Start thread for service and console.
    service_th = threading.Thread(target=system_service)
    console_th = threading.Thread(target=console_service)
    
    service_th.start()
    console_th.start()

    time.sleep(3)   # short delay to start service and console threads

    # Setup PCAP Capture Threads for each interface to monitor.
    d = Data()
    capture_pcap = False
    capture_pcap = d.get_config_value(Config.SERVICE_PCAPS_ACTIVE)

    pcap_th = []

    if capture_pcap:
        interval = int(d.get_config_value(Config.SERVICE_PCAP_INTERVAL))
        maximum =  int(d.get_config_value(Config.SERVICE_PCAP_COUNT))
        interfaces = d.get_config_value(Config.SERVICE_PCAP_INTERFACES).replace(" ", "").split(",")

        for interface in interfaces:
            th = threading.Thread(target=pcap, args=(interface, interval, maximum)) 
            th.start()
            pcap_th.append(th)
        
    # Join all threads for shutdown.
    for th in pcap_th:
        th.join()

    service_th.join()
    console_th.join()


    # Shutdown
    logger.warningprint("Exiting Perseus.")   
    graceful_shutdown = True                        # Tells Service Stop loop that shutdown is complete.


if __name__ == "__main__":
    main()
