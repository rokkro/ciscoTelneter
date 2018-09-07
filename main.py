# DO NOT USE THIS SCRIPT IN PLACES WHERE SECURITY IS IMPORTANT! Telnet is NOT a secure protocol.
# This script is used in an isolated student/education environment.
# It serves as a simple way for a lab assistant to reset device configurations after students do lab assignments.
# Used for resetting Cisco IOS 12.X switches/routers.
# This script is not yet fully automatic at the moment,since a new config file needs to be selected using the menu UI.
# Running this in an IDE will probably not display the password prompt, given how getpass() works.
from telnetlib import Telnet
import getpass, socket, os

# PUT THE STARTING DIRECTORY FOR LOCATING CONFIG FILES HERE
# Tip: you can use forward slashes instead of backslashes on Windows
CONFIGS_ROOT_DIR = "//ATLAS/Repos/Cisco Configurations/Static/"


class Menu:
    colors = {
        "purple": "\033[1;94m",
        "yellow": '\33[33m',
        "end": '\033[1;0m',
    }
    horizontal_len = 40
    key_queue = []

    def header(self, text):  # ---header text---
        print(self.colors['yellow'] + text + self.colors['end'])

    def divider(self):  # ----------
        print(self.colors['end'] + self.colors['yellow'] + '-' * self.horizontal_len + self.colors['end'])

    def get_menu(self, head, menu, input_menu):
        # Numbered user input menu
        while True:
            if not menu:
                print("There doesn't appear to be anything here...")
                return ''
            if menu is not None:
                self.header(head)
                for num, entry in enumerate(menu):  # Print entries
                    print("[" + self.colors['purple'] + str(num + 1) + self.colors['end'] + "] - " + str(entry))
                self.divider()
            if not self.key_queue:
                # Stylize input menu
                entry = input(self.colors['end'] + input_menu.replace("[", self.colors['end'] +
                                                                      "[" + self.colors['purple']).replace("]",
                                                                                                           self.colors[
                                                                                                               'end'] + "]" +
                                                                                                           self.colors[
                                                                                                               'end'])).strip()
                if len(entry.split(" ")) > 1:
                    entries = entry.split(" ")
                    entry = entries[0]
                    del entries[0]
                    self.key_queue.extend(entries)
            else:
                entry = self.key_queue[0]
                del self.key_queue[0]
            if entry == 'q':  # input 'q' to quit
                quit()
            elif entry == '':  # Returns space for menus to handle it.
                return entry
            try:  # Type cast num input to int
                entry = int(entry)
            except ValueError:
                continue
            if ((entry > len(menu)) if menu is not None else False) or entry < 1:
                # (Compare entry to menu size if the menu exists, otherwise False) OR if input is < 1
                continue  # Recognize as invalid input
            return entry  # Successfully return input for menus to handle

    def get_path_menu(self, path="./"):
        """
        Saves original working dir in cwd. Gets abs path of input dir, and changes to it.
          Creates menu from that dir. If ENTER is pressed, go up a dir. If a dir is selected, change to it.
          Rinse and Repeat. Convert final file path to abspath, and cut out file name from it. Change to original cwd.
          Return absolute path and the file name (strings).
        """
        cwd = os.getcwd()

        def set_file(path):
            path = os.path.abspath(path)
            os.chdir(path)
            while True:
                files = os.listdir("./")
                menu_display = []
                # Appending a "/" to dirnames here so it's easy to differentiate between files and dirs in the menu UI.
                for i in files:
                    if os.path.isdir("./" + i):
                        menu_display.append(i + "/\t->(" + str(len(os.listdir("./" + i))) + ")")
                    else:
                        menu_display.append(i)
                inpt = self.get_menu(path, menu_display, "*Enter a file/dir number or [Enter] - go up a dir.\n>>>")
                if inpt == '':
                    os.chdir("..")
                    continue
                selected = files[inpt - 1]
                if os.path.isdir("./" + selected):
                    os.chdir(selected)
                    continue
                return selected

        selected_file = set_file(path)
        if selected_file is None:
            return
        file_abs = os.path.abspath(selected_file).replace(selected_file, "")
        os.chdir(cwd)
        return file_abs, selected_file


class TeleCisc:
    PORT = 23
    STORE_PASSWD = True
    READ_TIMEOUT = 3
    CONNECT_TIMEOUT = 10
    PRIVILEGED = "privileged"
    UNPRIVILEGED = "unprivileged"
    IOS_SYNTAX = {
        "username": "Username:",
        "password": "Password:",
        "login_fail": "% Bad",
        "unprivileged": ">",
        "privileged": "#",
        "more": "--More--",
        "host": "hostname",
    }

    def __init__(self):
        self.username = ""
        self.host = ""
        self.password = ""  # Only used if STORE_PASSWD is True
        self.connection = None
        self.mode = ""
        self.running_config = []
        self.startup_config = []
        self.config_file = []
        self.config_file_name = ""
        self.config_file_path = ""
        self.tftp_server_active = False

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

    def ios_fetch_and_store_conf(self):
        print("\n---Device Configuration Read---")
        if not self.PRIVILEGED:
            self.ios_read()
        print("Changing terminal length...")
        # Prevents --more-- prompt from showing, causing issues with CRLFs
        self.connection.write("terminal length 0".encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        print("Reading running-config and startup-config...")

        def read_conf(store_list, file_name):
            self.connection.write(("show " + file_name).encode("ascii") + b"\n")
            self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
            while True:
                line = self.connection.read_until(b"\r\n", timeout=self.READ_TIMEOUT)
                if not line:
                    break
                line = line.strip().decode()
                store_list.append(line)

        read_conf(self.startup_config, "startup-config")
        print("startup-config read:",self.startup_config)
        read_conf(self.running_config, "running-config")
        print("running-config read:",self.running_config)

    def ios_read(self):
        print("\n---Command Line Access---")
        while True:
            line = self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)
            if not line.strip():
                continue
            ### LOGIN STUFF ###
            if self.IOS_SYNTAX["username"] in line.decode():
                while not self.username:
                    self.username = input("Username: ")
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
                print("Logged in...\nEntering Privileged Mode...")
                self.connection.write("enable".encode("ascii") + b"\n")
                continue
            elif self.IOS_SYNTAX["privileged"] in line.decode():
                self.mode = self.PRIVILEGED
                print("Entered Privileged Mode.")
                break
            else:
                continue

    def config_file_selection(self):
        print("\n---Configuration File Selection---")
        if not CONFIGS_ROOT_DIR:
            print("***Change CONFIGS_ROOT_DIR in the script to a config file location!***")
        while True:
            abs_path, file_name = Menu().get_path_menu(CONFIGS_ROOT_DIR)
            config_as_list = list(i.strip() for i in open(abs_path + file_name))
            print(config_as_list)
            host_name = "".join([i for i in config_as_list if self.IOS_SYNTAX["host"] in i.strip()])
            print("PATH: " + abs_path + file_name + "\nHOSTNAME: " + host_name if host_name else "(not found in file)")
            good_file = input("Continue using this file? [y/n]:")
            if good_file.strip().lower() in ["y", "yes"]:
                self.config_file = config_as_list
                self.config_file_path = abs_path
                self.config_file_name = file_name
                break
            else:
                continue
        print("File selected!")

    def ios_tclsh(self):
        print("\n---TCLSH File Creation---")
        if not self.PRIVILEGED:
            self.ios_read()
        print("Entering tcl shell...")
        self.connection.write("tclsh".encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.write("puts [open \"flash:temp.txt\" w+]{".encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
#https://howdoesinternetwork.com/2018/create-file-cisco-ios
    def telnet_to_device(self):
        print("\n---Device Connection---")
        self.initial_connect()
        print("Attempting connection to " + self.host + "...")
        try:
            self.connection = Telnet(self.host, self.PORT, timeout=self.CONNECT_TIMEOUT)
        except socket.gaierror as e:
            # Kill connection when it fails
            print("Connection to host failed:", e)
            self.connection = None
            quit()
        print("Connection Succeeded!\nWaiting for log in prompt...")


    def run(self):
        self.config_file_selection()
        self.telnet_to_device()
        try:
            self.ios_read()
            # self.ios_fetch_and_store_conf()
        except (ConnectionAbortedError, EOFError) as e:
            print("Telnet connection died:", e)

TeleCisc().run()
