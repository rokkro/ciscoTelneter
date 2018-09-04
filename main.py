# This script does not use secure protocols, as it is used in an education environment.
from telnetlib import Telnet
import getpass, socket


class TeleCisc:
    PORT = 23
    STORE_PASSWD = True
    PRIVILEGED = "privileged"
    UNPRIVILEGED = "unprivileged"
    IOS_SYNTAX = {
        "username": "Username:",
        "password": "Password:",
        "login_fail": "% Bad",
        "unprivileged": ">",
        "privileged": "#",
        "more": "--More--"
    }

    def __init__(self):
        self.username = ""
        self.host = ""
        self.password = ""  # Only used if STORE_PASSWD is True
        self.connection = None
        self.mode = ""
        self.running_config = []
        self.startup_config = []

    def input_password(self):
        passwd = ""
        if self.STORE_PASSWD and self.password:
            return self.password
        while not passwd:
            # getpass() does not work in normal IDE, use debug mode or the command line
            passwd = getpass.getpass('Password: ')
        if self.STORE_PASSWD:
            self.password = passwd
        return passwd

    def initial_connect(self):
        while not self.host:
            self.host = input("IP or Hostname: ")
        while not self.username:
            self.username = input("Username: ")

    def ios_fetch_and_store_conf(self):
        if not self.PRIVILEGED:
            self.ios_read()
        print("Reading running-config and startup-config...")
        def read_conf(list, file_name):
            self.connection.write(("show " + file_name).encode("ascii") + b"\n")
            line = self.connection.read_until(b"\n", timeout=5).decode().strip()
            while line.strip():
                line = self.connection.read_until(b"\n", timeout=5).decode().strip()
                if self.IOS_SYNTAX["more"] in line:
                    self.connection.write(b" ")
                    continue
                list.append(line)
                print(line)

        read_conf(self.startup_config,"startup-config")
        read_conf(self.running_config,"running-config")


    def ios_read(self):
        while True:
            line = self.connection.read_until(b"\n", timeout=5)
            if not line.strip():
                continue
            ### LOGIN STUFF ###
            if self.IOS_SYNTAX["username"] in line.decode():
                self.connection.write(self.username.encode('ascii') + b"\n")
                self.connection.interact()
                continue
            elif self.IOS_SYNTAX["password"] in line.decode():
                self.connection.write(self.input_password().encode('ascii') + b"\n")
                continue
            elif self.IOS_SYNTAX["login_fail"] in line.decode():
                print("Bad Password!")
                continue
            ### MODE STUFF ###
            elif self.IOS_SYNTAX["unprivileged"] in line.decode():
                self.mode = self.UNPRIVILEGED
                print("Logged in... Entering Privileged Mode...")
                self.connection.write("enable".encode("ascii") + b"\n")
                continue
            elif self.IOS_SYNTAX["privileged"] in line.decode():
                self.mode = self.PRIVILEGED
                print("Entered Privileged Mode.")
                break
            else:
                continue

    def connect(self):
        self.initial_connect()
        print("Attempting connection to " + self.host + "...")
        try:
            self.connection = Telnet(self.host, self.PORT, timeout=10)
        except socket.gaierror as e:
            # Kill connection when it fails
            print("Connection to host failed:", e)
            self.connection = None
            quit()
        print("Connection Succeeded! Waiting for log in prompt...")
        try:
            self.ios_read()
            self.ios_fetch_and_store_conf()
            self.connection.interact()
        except ConnectionAbortedError as e:
            print("Telnet connection died:",e)

TeleCisc().connect()
