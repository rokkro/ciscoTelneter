# DO NOT USE THIS SCRIPT IN PLACES WHERE SECURITY IS IMPORTANT! Telnet is NOT a secure protocol.
# This script is used in an isolated student/education environment.
# It serves as a simple way for a lab assistant to reset device configurations after students do lab assignments.
# Used for resetting Cisco IOS 12.X switches/routers.
# This script is not yet fully automatic at the moment,since a new config file needs to be selected using the menu UI.
# Running this in an IDE will probably not display the password prompt, given how getpass() works.
from mini_menu import Menu
from telnetlib import Telnet
import getpass
import socket

# PUT THE STARTING DIRECTORY FOR LOCATING CONFIG FILES HERE
# You can use forward slashes instead of backslashes on Windows
CONFIGS_ROOT_DIR = ""


class TeleCisc:
    PORT = 23
    STORE_PASSWD = False
    DEBUG_MODE = True
    READ_TIMEOUT = 3
    CONNECT_TIMEOUT = 10
    TEMP_FILE_NAME = "temp.txt"
    PRIVILEGED = "privileged"
    UNPRIVILEGED = "unprivileged"

    def __init__(self):
        self.username = ""
        self.host = ""
        self.password = ""  # Only used if STORE_PASSWD is True
        self.connection = None
        self.config_list_tmp = []
        self.config_file = []
        self.config_file_name = ""
        self.config_file_path = ""
        self.mode = self.UNPRIVILEGED

    def ios_change_term_length(self, length):
        print("Changing terminal length...")
        # Prevents --more-- prompt from showing, causing issues with CRLFs
        self.connection.write(("terminal length " + str(length)).encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work

    def ios_fetch_and_store_conf(self, file_name, store_list, view_command="more"):
        # view_command should be "more" for files in flash, and "show" for startup-config, running-config, etc.
        print("\n---Reading file", file_name + "---")
        if self.mode == self.UNPRIVILEGED:
            self.ios_login_and_elevate()
        self.ios_change_term_length(0)
        self.connection.write((view_command + " " + file_name).encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        # Jump a couple lines so the above commands aren't read into the store_list
        self.connection.write("\r\n".encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)
        self.connection.write("\r\n".encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)
        while True:
            # Read every line of file, storing it in store_list
            line = self.connection.read_until(b"\r\n", timeout=self.READ_TIMEOUT)
            # If empty line, assume done reading file
            if not line.strip():
                break
            # Remove CRLFs without using strip(), which removes all spacing.
            line = line.replace(b"\r", b"").replace(b"\n", b"").decode()
            store_list.append(line)

    def ios_login_and_elevate(self):
        print("\n---CLI Login---")
        while True:
            line = self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)
            if not line.strip():
                continue
            # LOGIN STUFF #
            if "Username:" in line.decode():
                while not self.username:
                    self.username = input("Username: ")
                self.connection.write(self.username.encode('ascii') + b"\n")
                self.connection.interact()
                continue
            elif "Password:" in line.decode():
                self.connection.write(self.input_password().encode('ascii') + b"\n")
                continue
            elif "% Bad" in line.decode():
                print("Bad Password!")
                self.password = ""
                self.username = ""
                continue
            # MODE STUFF #
            elif ">" in line.decode():
                self.mode = self.UNPRIVILEGED
                print("Logged in...\nEntering Privileged Mode...")
                self.connection.write("enable".encode("ascii") + b"\n")
                continue
            elif "#" in line.decode():
                self.mode = self.PRIVILEGED
                print("Entered Privileged Mode.")
                break
            else:
                continue

    def ios_tclsh(self):
        # https://howdoesinternetwork.com/2018/create-file-cisco-ios
        # Deals with tcl shell to create a temporary text file
        # This file can then be copied to the startup-config
        # This is done instead of using the configuration mode, as we want to add a fresh config file and not
        #   have to worry about leftover settings being retained.
        print("\n---Tclsh File Creation---")
        if self.mode == self.UNPRIVILEGED:
            self.ios_login_and_elevate()
        print("Entering tcl shell...")
        self.connection.write("tclsh".encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        print("Writing config file to", self.TEMP_FILE_NAME + "...")
        # Create new file in flash named temp.txt
        # puts is picky about how it determines line endings. Can't use \n, so \r was used instead.
        self.connection.write(
            ("puts -nonewline [open \"flash:" + self.TEMP_FILE_NAME + "\" w+] {").encode("ascii") + b"\r")
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        # For every line in the config file on disk, write to the temporary file
        for line in self.config_file:
            if not line:
                continue
            self.connection.write(line.encode("ascii") + b"\r")
            self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        # End the file
        self.connection.write("}".encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        # Exit the tcl shell
        self.connection.write("tclquit".encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        # Read through temp.txt, put in a list to make sure everything was copied correctly
        self.ios_fetch_and_store_conf(self.TEMP_FILE_NAME, self.config_list_tmp)
        # Print contents of temp.txt
        print(self.config_list_tmp)

    def ios_copy_to_config(self, temporary_file="temp.txt", config_to_copy_to="startup-config"):
        print("---Copying", temporary_file, "to", config_to_copy_to + "---")
        self.connection.write(("copy " + self.TEMP_FILE_NAME + " startup-config").encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.write("startup-config".encode("ascii") + b"\n")
        # Get through all the copy prompts
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.write(b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work

    def ios_reload(self):
        print("---Reloading device and exiting program---")
        self.connection.write("reload".encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.write(b"yes\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work

    def ios_remove_temp_file(self):
        print("Deleting " + self.TEMP_FILE_NAME + "...")
        self.connection.write(("delete flash:" + self.TEMP_FILE_NAME).encode("ascii") + b"\n")
        # Get through all the delete prompts
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.write(b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.write(b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work

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

    def input_host(self):
        while not self.host:
            self.host = input("IP or Hostname: ")

    def config_file_selection(self):
        print("\n---Configuration File Selection---")
        if not CONFIGS_ROOT_DIR:
            print("***Change CONFIGS_ROOT_DIR in the script to a config file location!***")
        while True:
            abs_path, file_name = Menu().get_path_menu(CONFIGS_ROOT_DIR)
            # Have to strip here
            config_as_list = list(i.replace("\n", "").replace("\r", "") for i in open(abs_path + file_name))
            print(config_as_list)
            host_name = "".join([i for i in config_as_list if "hostname" in i.strip()])
            host_name = host_name.replace("hostname", "").strip()
            print("PATH: " + abs_path + file_name + "\nHOSTNAME: " + host_name if host_name else "(not found in file)")
            good_file = input("Continue using this file? [y/n]:")
            if good_file.strip().lower() in ["y", "yes"]:
                self.config_file = config_as_list
                self.config_file_path = abs_path
                self.config_file_name = file_name
                if host_name:
                    use_this_host = input("Attempt to connect to device with this hostname? [y/n]:")
                    if use_this_host.strip().lower() in ["y", "yes"]:
                        self.host = host_name
                break
            else:
                continue
        print("File selected!")

    def telnet_to_device(self):
        print("\n---Device Connection---")
        self.input_host()
        print("Attempting connection to " + self.host + "...")
        try:
            self.connection = Telnet(self.host, self.PORT, timeout=self.CONNECT_TIMEOUT)
        except socket.gaierror as e:
            # Kill connection when it fails
            print("Connection to host failed:", e)
            quit()
        except socket.timeout as e:
            print("Connection to host failed:", e)
            quit()
        print("Connection Succeeded!\nWaiting for log in prompt...")

    def run(self):
        while True:
            # Select backup config file from disk
            self.config_file_selection()
            # Do a telnet connection to device
            self.telnet_to_device()
            if self.DEBUG_MODE:
                # Print extra console output
                self.connection.set_debuglevel(2)
            try:
                # Login, elevate privileges
                self.ios_login_and_elevate()
                # Enter TCL shell, write config file to temporary file
                self.ios_tclsh()
                if not input("Try to copy this config to the startup-config? [y/n]:").strip().lower() in ['y', 'yes']:
                    self.host = ""
                    self.connection = None
                    self.username = ""
                    self.password = ""
                    continue
                # Copy temporary file to startup-config
                self.ios_copy_to_config()
                # Remove temporary file
                self.ios_remove_temp_file()
                if input("Reload device to use new config? [y/n]:").strip().lower() in ['y', 'yes']:
                    self.ios_reload()
                    quit()
            except (ConnectionAbortedError, EOFError) as e:
                print("Telnet connection died:", e)


TeleCisc().run()
