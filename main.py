# This script does not use secure protocols
from telnetlib import Telnet
import getpass, socket


class TeleCisc:

    PORT = 23
    IOS_SYNTAX = {
        "username" : "Username:",
        "password" : "Password:",
        "login_fail" : "% Bad",
        "unprivileged" : ">",
        "privileged" : "#",
    }
    
    def __init__(self):
        self.username = ""
        self.host = ""
        self.password = ""  # Only used if store_passwd param is True in input_password()
        self.connection = None
        self.mode = ""

    def input_password(self, store_passwd):
        passwd = ""
        if store_passwd and self.password:
            return self.password
        while not passwd:
            # getpass() does not work in normal IDE, use debug mode or the command line
            passwd = getpass.getpass('Password: ')
        if store_passwd:
            self.password = passwd
        return passwd

    def initial_connect(self):
        while not self.host:
            self.host = input("IP or Hostname: ")
        while not self.username:
            self.username = input("Username: ")

    def ios_store_running_conf(self):
        pass

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
                self.connection.write(self.input_password(True).encode('ascii') + b"\n")
                continue
            elif self.IOS_SYNTAX["login_fail"] in line.decode():
                print("Bad Password!")
                continue
            ### MODE STUFF ###
            elif self.IOS_SYNTAX["unprivileged"] in line.decode():
                self.mode = "unprivileged"
                print("Logged in... Entering Privileged Mode...")
                self.connection.write("enable".encode("ascii") + b"\n")
                continue
            elif self.IOS_SYNTAX["privileged"] in line.decode():
                self.mode = "unprivileged"
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
            print("Connection to host failed:",e)
            self.connection = None
            quit()
        print("Connection Succeeded! Waiting for log in prompt...")
        self.ios_read()
        self.connection.interact()


TeleCisc().connect()
