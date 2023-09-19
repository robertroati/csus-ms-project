import os
import logging
import logging.handlers


class Syslog: 

    def __init__(self, server_ip, udp_port=514):
        self.hostname = os.popen('hostname').read().strip()

        self.logger = logging.getLogger(self.hostname)
        self.logger.setLevel(logging.INFO)
        self.syslog_handler = logging.handlers.SysLogHandler(address=(server_ip, udp_port), facility=logging.handlers.SysLogHandler.LOG_USER)
        self.syslog_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(self.syslog_handler)
        self.logger.info('Syslog initialized.')

    def setLevel(self, n):
        if n == 1:
            self.logger.setLevel(logging.DEBUG)
        if n == 2:
            self.logger.setLevel(logging.INFO)
        if n == 3:
            self.logger.setLevel(logging.WARNING)
        if n == 4:
            self.logger.setLevel(logging.ERROR)
        if n == 5:
            self.logger.setLevel(logging.CRITICAL)


    def debug(self, message):
        self.setLevel(1)
        self.logger.debug(message)

    def info(self, message):
        self.setLevel(2)
        self.logger.info(message)

    def warning(self, message):
        self.setLevel(3)
        self.logger.warning(message)

    def error(self, message):
        self.setLevel(4)
        self.logger.error(message)

    def critical(self, message):
        self.setLevel(5)
        self.logger.critical(message)

    def infoprint(self, message):
        print(message)
        self.info(message)

    def warningprint(self, message):
        print(message)
        self.warning(message)
    
    def errorprint(self, message):
        print(message)
        self.error(message)

    def criticalprint(self, message):
        print(message)
        self.critical(message)