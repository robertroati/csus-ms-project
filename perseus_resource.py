from enum import Enum

class Table(Enum):
    CONFIG = "perseus_config"
    FILES = "perseus_files"
    FILECHG = "perseus_file_change"
    COMMANDS = "perseus_commands"
    COMMANDCHG = "perseus_command_change"
    PROCESSES = "perseus_processes"
    DEVICES = "perseus_devices"


class Config(Enum):
    SYSTEM_DEVICE_ID = 'device_id'
    SYSTEM_CONSOLE_PW = 'console_pw'
    SYSTEM_CONSOLE_TIMEOUT = 'console_timeout'
    SYSTEM_UNLOCK_USER = 'unlock_username'
    SYSTEM_UNLOCK_PW = 'unlock_password'
    SYSTEM_USER_ACTIVITY_LOG = 'user_activity_log'
    SYSLOG_HOST = 'syslog_host'
    SYSLOG_PORT = 'syslog_port'
    SFTP_HOST = 'sftp_host'
    SFTP_PORT = 'sftp_port'
    SFTP_DIR = 'sftp_remote_dir'
    SFTP_USER = 'sftp_user'
    SFTP_PW = 'sftp_password'
    SERVICE_PCAPS_ACTIVE = 'capture_pcaps'
    SERVICE_PCAP_INTERVAL = 'pcap_interval'
    SERVICE_PCAP_COUNT = 'maximum_pcaps'
    SERVICE_PCAP_INTERFACES = 'capture_interfaces'
    SERVICE_HEARTBEAT_INTERVAL = 'heartbeat_interval'
    SERVICE_FILE_INTERVAL = 'file_check_interval'
    SERVICE_COMMAND_INTERVAL = 'command_check_interval'
    SERVICE_PROCESS_INTERVAL = 'process_check_interval'
    SERVICE_DEVICE_INTERVAL = 'device_check_interval'
    CONTACT_NAME = 'contact_name'
    CONTACT_EMAIL = 'contact_email'
    CONTACT_PHONE = 'contact_phone'

class Service(Enum):
    OK                          = 0
    CHECK                       = 1
    LOGIN                       = 7
    LOGIN_FAILURE               = 17
    LOGOUT                      = 23
    GET_CONTACT                 = 30
    GET_DATA                    = 2
    GET_SELECTION               = 3
    GET_CONFIG_VALUE            = 4
    GET_VALUE                   = 5
    APPROVE_ALL_PROCESSES       = 11  
    APPROVE_ALL_DEVICES         = 12
    APPROVE_DEVICE_TOGGLE       = 15
    APPROVE_PROCESS_TOGGLE      = 16
    INSERT_MONITOR              = 37
    UPDATE_MONITOR              = 36
    UPDATE_PW                   = 33
    UPDATE_CONFIG               = 31
    UPDATE_VALUE                = 6
    UPLOAD_DB                   = 51
    UPLOAD_LOGS                 = 52
    UPLOAD_ALL                  = 50
    SHUTDOWN                    = 101
    LOCKDOWN                    = 102
    ERROR                       = -1



    @staticmethod 
    def getServiceE(value):
        for member in Service:
            if member.value == value:
                return member
        return None  
