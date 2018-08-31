# This script does not use secure protocols
from telnetlib import Telnet
import getpass, socket, time


class teleCisc:
    PORT = 23
    
    def __init__(self):
        self.username = ""
        self.host = ""
        self.tn = None
        self.mode = ""

    @staticmethod
    def input_passwd():
        passwd = ""
        while not passwd:
            # getpass() does not work in normal PyCharm run mode, use debug mode
            passwd = getpass.getpass('Password: ')
        return passwd

    def user_input_cli(self):
        while not self.host:
            self.host = input("IP or Hostname: ")
        while not self.username:
            self.username = input("Username: ")

    def device_login(self):
        def get_password():
            return self.input_passwd()
        while True:
            login = self.tn.read_until(b"\n",timeout=2)
            if "Username:" in login.decode():
                self.tn.write(self.username.encode('ascii') + b"\n")
                self.tn.interact()
                continue
            elif "Password:" in login.decode():
                self.tn.write(get_password().encode('ascii') + b"\n")
                self.tn.interact()
                continue
            elif "% Bad" in login.decode():
                print("Bad Password!")
                continue
            elif ">" in login.decode():
                self.mode = "unprivileged"
                passwd = None
                break
            else:
                continue

    def connect(self):
        self.user_input_cli()

        print("Attempting connection to " + self.host + "...")
        try:
            self.tn = Telnet(self.host,self.PORT,timeout=10)
        except socket.gaierror as e:
            print("Connection to host failed:",e)
            self.tn = None
            quit()
        print("Connection Succeeded!")
        self.device_login()
        self.tn.interact()


teleCisc().connect()