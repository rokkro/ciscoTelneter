# This script does not use secure protocols
from telnetlib import Telnet
import getpass, socket


class TeleCisc:

    PORT = 23
    
    def __init__(self):
        self.username = ""
        self.host = ""
        self.tn = None
        self.mode = ""

    @staticmethod
    def input_password():
        passwd = ""
        while not passwd:
            # getpass() does not work in normal IDE, use debug mode or the command line
            passwd = getpass.getpass('Password: ')
        return passwd

    def initial_connect(self):
        while not self.host:
            self.host = input("IP or Hostname: ")
        while not self.username:
            self.username = input("Username: ")

    def ios_read(self):
        while True:
            login = self.tn.read_until(b"\n",timeout=2)
            ### LOGIN STUFF ###
            if "Username:" in login.decode():
                self.tn.write(self.username.encode('ascii') + b"\n")
                self.tn.interact()
                continue
            elif "Password:" in login.decode():
                self.tn.write(self.input_password().encode('ascii') + b"\n")
                self.tn.interact()
                continue
            elif "% Bad" in login.decode():
                print("Bad Password!")
                continue
            ### MODE STUFF ###
            # TODO: Verify modes are working fine, edge cases
            elif ">" in login.decode():
                self.mode = "unprivileged"
                break
            elif "#" in login.decode():
                self.mode = "unprivileged"
                break
            else:
                continue

    def connect(self):
        self.initial_connect()
        print("Attempting connection to " + self.host + "...")
        try:
            self.tn = Telnet(self.host,self.PORT,timeout=10)
        except socket.gaierror as e:
            # Kill connection when it fails
            print("Connection to host failed:",e)
            self.tn = None
            quit()
        print("Connection Succeeded!")
        self.ios_read()
        self.tn.interact()


TeleCisc().connect()
