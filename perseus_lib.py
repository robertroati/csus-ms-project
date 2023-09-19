import datetime as dt
import hashlib
import os
import psutil
import pyudev
import pwd
import shlex
import subprocess
import sys
import tty
import termios


class Library: 

    @staticmethod
    def datetime():
        return dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')



    @staticmethod
    def date():
        return dt.datetime.now().strftime('%Y-%m-%d')



    @staticmethod
    def setTimer(s):
        return dt.datetime.now() + dt.timedelta(seconds=s)



    @staticmethod
    def isExpired(t):
        if (t < dt.datetime.now()):
            return True
        else:
            return False


    @staticmethod
    def get_session_id():
        return hashlib.sha256(str(dt.datetime.now()).encode()).hexdigest()[:32]


    @staticmethod
    def getStrHash(text):
        if isinstance(text, str):
            return hashlib.sha256(text.encode('utf-8')).hexdigest()
        else:
            return None



    @staticmethod
    def getFileHash(f):
        if os.path.exists(f):
            return hashlib.sha256(open(f,'rb').read()).hexdigest()
        else:
            return None



    @staticmethod
    def checkFileForString(f, substring):
        if os.path.exists(f):
            try:
                with open(f, 'r') as file:
                    file_text = file.read()
                    if substring in file_text:
                        return True
                return False
            except Exception as e:
                print(f"An error occurred: {e}")
                return False
        else:
            return False
        


    @staticmethod
    def getProcessInfo():
        result = subprocess.run(['ps', '-e', '-o', 'pid,comm,cmd'], stdout=subprocess.PIPE, text=True)
        output = result.stdout.strip()
        lines = output.split('\n')[1:]  # Skip the header line
        
        # Prevent tracking duplicate cmdline commands, and ignore root/capture commands
        unique_cmds = set()
        unique_cmds.add("/sbin/init splash")            # Exclude root processs (w/ GUI)
        unique_cmds.add("/sbin/init")                   # Exclude root process (w/o GUI)
        unique_cmds.add("ps -e -o pid,comm,cmd")        # Exclude capture command.
        unique_cmds.add("sleep 1")                      # Exclude sleep command.
        unique_cmds.add("sleep 5")                      # Exclude sleep command.
        unique_cmds.add("sleep 10")                     # Exclude sleep command.

        processes = []
        for line in lines:
            fields = line.split(None, 2)  # split on white space, except for find cmdline field. 
            
            # Skip any cmd wrapped in '[]' (system processes).
            if not (fields[2].startswith('[') and fields[2].endswith(']')):
                if (fields[2] not in unique_cmds):
                    unique_cmds.add(fields[2])
                    processes.append(fields[1:])    # Remove PID
            
        return processes
    


    @staticmethod
    def getDeviceInfo():
        context = pyudev.Context()
        device_types = ['block','usb','scsi','mmc']

        device_list = []
        for device in context.list_devices():
            if device.subsystem in device_types:
                # Ignore loop devices
                if (not device.device_type == 'disk') and (not device.sys_name.startswith('loop')): 
                    device_list.append([device.sys_name, device.device_type])

        return device_list



    @staticmethod
    def createUser(user, pw):
        try:
            # Create user
            subprocess.run(['useradd', '-m', user], check=True)

            # Set user password
            p = subprocess.Popen(['passwd', user], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate(input=f"{pw}\n{pw}\n".encode('utf-8'))
            
            if p.returncode != 0:
                print(f"Failed to set password: {stderr.decode('utf-8')}")
                return False

            return True

        except subprocess.CalledProcessError as e:
            print(f"Error creating user: {e}")
            return False



    @staticmethod
    def getPipedCommandOutput(command_text):
        try:
            processes = []
            split_command = command_text.split(" | ")
            cmd_output = None

            # First command in the pipe
            command_and_args = shlex.split(split_command[0])
            proc = subprocess.Popen(command_and_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            processes.append(proc)

            # For the subsequent commands in the pipe
            for cmd_segment in split_command[1:]:
                cmd_and_args = shlex.split(cmd_segment)
                proc = subprocess.Popen(cmd_and_args, stdin=processes[-1].stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # Feed pipe to previous process before closing.
                processes[-1].stdout.close()
                processes.append(proc)

                cmd_output, _ = processes[-1].communicate()
                                
        except FileNotFoundError:
            print("Command not found.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        return cmd_output



    @staticmethod
    def getCommandOutput(command_text):

        if " | " in command_text:
            return Library.getPipedCommandOutput(command_text)
        else:
            cmd_output = None

            try:
                command_list = shlex.split(command_text)
                process_output = subprocess.run(command_list, capture_output=True, text=True)
                cmd_output = process_output.stdout

            except subprocess.CalledProcessError as e:
                print(f"Command error output: {e.stderr}")

            except FileNotFoundError:
                print(f"Command '{command_text}' not found.")

            except Exception as e:
                print(f"An unexpected error occurred: {e}")

            return cmd_output
        

    @staticmethod
    def disableEthInterfaces():
        return Library.setEthInterfaces("down")


    @staticmethod
    def enableEthInterfaces():
        return Library.setEthInterfaces("up")


    @staticmethod
    def setEthInterfaces(state):

        modified_interfaces = []

        interface_addrs = psutil.net_if_addrs()
        interface_names = list(interface_addrs.keys())
            
        for ni in interface_names:
            if ni != "lo":
                try:
                    subprocess.run(["sudo", "ip", "link", "set", ni, state], check=True)
                    modified_interfaces.append(ni)
                except subprocess.CalledProcessError as e:
                     print(f"An error occurred modifying {ni}: {e}")

        return modified_interfaces



    @staticmethod
    def lockUserAccounts(excluded):

        locked_accounts = []

        for p in pwd.getpwall():
            user = p.pw_name
            shell = p.pw_shell

            # Exclude provided user list
            if user not in excluded:
                # Exclude non-shell accounts
                if shell != '/usr/sbin/nologin' or shell != '/bin/false':
                    # Lock the user account
                    try:
                        subprocess.run(["sudo", "passwd", "-l", user], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        locked_accounts.append(user)
                    except subprocess.CalledProcessError as e:
                        print(f"An error occurred locking {user}'s account: {e}")

        return locked_accounts


    @staticmethod
    def terminateUserSessions():

        terminated_sessions = []

        try:
            who_output = subprocess.check_output(["who"], text=True)
            lines = who_output.strip().split("\n")
            for l in lines:
                f = l.split()
                pid = f[1]
                subprocess.run(["sudo", "kill", "-9", pid], check=True)
                terminated_sessions.append(f[0])
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")

        return terminated_sessions
    

    def createMOTD(user):

        user_home = os.path.join("/home", user)
        motd_f = os.path.join(user_home, "perseus_motd.txt")
        brc_f = os.path.join(user_home, ".bashrc")

        motd = (f"The system was locked by Perseus on {Library.datetime()}.\n\n"
                "Network Interfaces have been disabled.\n"
                "Other user accounts have been locked."
                "The system can be unlocked in the Perseus Console.")

        if not os.path.exists(user_home):
            return False

        # write MOTD file
        with open(motd_f, "w") as f:
            f.write(motd)

        # add 'cat perseus_motd.txt' to user bashrc
        with open(brc_f, "a") as f:
            f.write(f"\ncat {motd_f}\n")

        return True