# DO NOT USE THIS SCRIPT IN PLACES WHERE SECURITY IS IMPORTANT! Telnet is NOT a secure protocol.
# This script is used in an isolated student/education environment.
# It serves as a simple way for a lab assistant to reset device configurations after students do lab assignments.
# Used for resetting Cisco IOS 12.X switches/routers.
# Running this in an IDE will probably not display the password prompt, given how getpass() works.

from mini_menu import Menu
from telnetlib import Telnet
from encodings.cp1252 import decoding_table
import getpass
import socket
import os

##################################################################
# PUT THE STARTING DIRECTORY FOR LOCATING CONFIG FILES HERE
# You can use forward slashes instead of backslashes on Windows
CONFIGS_ROOT_DIR = ""
##################################################################


class TeleCisc:
    PORT = 23
    SHOW_TELNET_OUTPUT = False
    READ_TIMEOUT = 3
    CONNECT_TIMEOUT = 10
    TEMP_FILE_NAME = "temp.txt"
    DELETE_TEMP_FILE = True

    def __init__(self):
        self.username = ""
        self.host = ""
        self.password = ""
        self.is_privileged_user = False
        self.connection = None
        self.config_list_tmp = []
        self.config_file = []
        self.config_file_name = ""
        self.config_file_path = ""
        self.configs_root_dir = CONFIGS_ROOT_DIR

    def ios_change_term_length(self, length):
        # Change terminal length to selected value. length = 0 is probably what you want.
        # Prevents --more-- prompt from showing, which causes issues with CRLFs
        print("Changing terminal length...")
        self.connection.write(("terminal length " + str(length)).encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work

    def ios_fetch_and_store_conf(self, file_name, store_list, view_command="more"):
        # Read a file (file_name) using the view_command. Store every line of that file in store_list
        # view_command should be "more" for files in flash, and "show" for startup-config, running-config, etc.
        print("\n---Reading file", file_name + "---")
        if not self.is_privileged_user:
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
            line = line.decode()
            line = self.remove_telnet_chars(line)
            store_list.append(line)

    def ios_login_and_elevate(self):
        # Get through username and password prompts and enter privileged mode.
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
                # self.connection.interact()
                continue
            elif "Password:" in line.decode():
                self.connection.write(self.input_password().encode('ascii') + b"\n")
                continue
            elif "% Bad" in line.decode() or "% Login invalid" in line.decode() or "% Access denied" in line.decode():
                print("Bad Login!")
                self.password = ""
                self.username = ""
                continue
            # MODE STUFF #
            elif ">" in line.decode():
                self.is_privileged_user = False
                print("Logged in...\nEntering Privileged Mode...")
                self.connection.write("enable".encode("ascii") + b"\n")
                continue
            elif "#" in line.decode():
                self.is_privileged_user = True
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
        if not self.is_privileged_user:
            self.ios_login_and_elevate()
        print("Entering tcl shell...")
        self.connection.read_until(b"\r\n", timeout=self.READ_TIMEOUT)  # Make written command work

        self.connection.write("tclsh".encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        # Ensure it actually enters the tcl shell
        self.connection.write(b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work

        print("Writing config file to", self.TEMP_FILE_NAME + "...")
        # Create new file in flash named temp.txt
        # puts is picky about how it determines line endings. Can't use \n, so \r was used instead.y
        self.connection.write(
            ("puts -nonewline [open \"flash:" + self.TEMP_FILE_NAME + "\" w+] {").encode('utf-8'))
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
        # Use copy config to copy from temp file to selected config file
        print("\n---Copying", temporary_file, "to", config_to_copy_to + "---")
        self.connection.write(("copy " + self.TEMP_FILE_NAME + " " + config_to_copy_to).encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.write(config_to_copy_to.encode("ascii") + b"\n")
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
        # Reload OS so it uses the new config
        print("\n---Reloading device and exiting program---")
        self.connection.write("reload".encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.write(b"yes\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work

    def ios_remove_temp_file(self):
        # Delete temporary file created to store config from tclsh
        print("\n---Cleanup---")
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
        # Use getpass() to prompt for user to enter password unless self.password already has something in it
        passwd = ""
        if self.password:
            return self.password
        # print("Displaying password prompt. If it does not show, use a different terminal application.\n")
        while not passwd:
            # getpass() does not work in normal IDE, use debug mode or the command line
            passwd = getpass.getpass('Password: ')
        self.password = passwd
        return passwd

    def input_host(self):
        while not self.host:
            self.host = input("IP or Hostname: ")

    @staticmethod
    def find_single_line_value(config_as_list, starts_with_field):
        # Look inside list for element str that starts with starts_with_field value, return it.
        #   return empty str if nothing found
        try:
            value = "".join([i for i in config_as_list if i.strip().startswith(starts_with_field)][0])
            value = value.replace(starts_with_field, "").strip()
            value = value.split(" ")[0].strip()  # Ensure there isn't extra garbage in the same line
            return value
        except IndexError:
            return ""

    def config_file_selection(self):
        # Display menu, prompt for file selection. Get config
        print("\n---Configuration File Selection---")
        if not self.configs_root_dir:
            print("***Change CONFIGS_ROOT_DIR in the script to a config file location!***")
            self.configs_root_dir = input("Enter an absolute path to a config file repository or a config file itself:")
        use_this_file = False
        while not use_this_file:
            try:
                if os.path.isdir(self.configs_root_dir):
                    abs_path, file_name = Menu().get_path_menu(self.configs_root_dir)
                    self.configs_root_dir = abs_path  # Move dir path here, in case user decides not to use file
                else:
                    abs_path = os.path.abspath(self.configs_root_dir)
                    file_name = abs_path[abs_path.rfind("\\") + 1:]
                    abs_path = abs_path.replace(file_name, "")
                    self.configs_root_dir = abs_path  # Move dir path here, in case user decides not to use file
            except Exception as e:
                print("Config path issue:", e, "\nExiting...")
                quit()
            # Remove CRLF without stripping spaces
            try:
                config_as_list = list(self.remove_telnet_chars(i) for i in open(abs_path + file_name))
            except (UnicodeDecodeError, OSError) as e:
                print("Bad file selected:", e)
                continue
            except FileNotFoundError as e:
                print("File selected does not exist:", e)
                continue
            print(config_as_list)
            use_this_file = self.config_file_selection_prompts(config_as_list, abs_path, file_name)

    def config_file_selection_prompts(self, config_as_list, abs_path, file_name):
        # Prompt for whether or not file should be used. Prompt for usage of hostname or password from config file
        host_name = self.find_single_line_value(config_as_list, "hostname")
        passwd = self.find_single_line_value(config_as_list, "password")
        username = self.find_single_line_value(config_as_list, "username")
        print("\nPATH: " + abs_path + file_name + "\nHOSTNAME: " + host_name if host_name else "(not found in file)")
        good_file = input("\nContinue using this file? [y/n]:")
        if good_file.strip().lower() in ["y", "yes"]:
            self.config_file = config_as_list
            self.config_file_path = abs_path
            self.config_file_name = file_name
            if host_name:
                use_this_host = input("\nAttempt to connect to device with hostname '" + host_name + "'? [y/n]:")
                if use_this_host.strip().lower() in ["y", "yes"]:
                    self.host = host_name
            if username:
                use_this_username = input(
                    "\nUsername '" + username + "' found in config. Try to use it to log in? [y/n]:")
                if use_this_username.strip().lower() in ["y", "yes"]:
                    self.username = username
            if passwd:
                use_this_pass = input("\nPassword found as plaintext in config. Try to use it to log in? [y/n]:")
                if use_this_pass.strip().lower() in ["y", "yes"]:
                    self.password = passwd
            return True
        else:
            return False

    def telnet_to_device(self):
        # Create telnet connection to host
        print("\n---Device Connection---")
        self.input_host()
        print("Attempting connection to " + self.host + "...")
        try:
            self.connection = Telnet(self.host, self.PORT, timeout=self.CONNECT_TIMEOUT)
            if self.SHOW_TELNET_OUTPUT:
                # Print extra console output
                self.connection.set_debuglevel(1)
        except (socket.gaierror, socket.timeout) as e:
            # Kill connection when it fails
            print("Connection to host failed:", e)
            quit()
        print("Connection Succeeded!\nWaiting for log in prompt...")

    def interact_with_device(self):
        # Calls device interaction functions, prompts user
        try:
            # Login, elevate privileges
            self.ios_login_and_elevate()
            # Enter TCL shell, write config file to temporary file
            self.ios_tclsh()
            prompt_for_reload = False
            if input("\nTry to copy this config to the startup-config? [y/n]:").strip().lower() in ['y', 'yes']:
                # Copy temporary file to startup-config
                prompt_for_reload = True
                self.ios_copy_to_config(config_to_copy_to="startup-config")
            if input("\nTry to copy this config to the running-config? [y/n]:").strip().lower() in ['y','yes']:
                # Copy temporary file to running-config
                # Don't prompt for reload if copied config to both running-config and startup-config
                prompt_for_reload = False
                self.ios_copy_to_config(config_to_copy_to="running-config")
            # Remove temporary file
            if self.DELETE_TEMP_FILE:
                self.ios_remove_temp_file()
            if prompt_for_reload and input("Reload device to use new startup-config? [y/n]:").strip().lower() in ['y', 'yes']:
                self.ios_reload()
            print("\n---DONE!---")
            quit()
        except (ConnectionAbortedError, EOFError) as e:
            print("Telnet connection died:", e)
            quit()

    @staticmethod
    def string_to_bytes_to_string(line, encoding='utf-8'):
        # Hacky way to make characters recognizable and replaceable:
        # Convert to bytes object with utf-8 encoding
        # Make it a (bytes) string: b'some string'
        # Splice string to remove the b''
        line = bytes(line, encoding=encoding, errors='ignore')
        line = str(line)
        line = line[2:len(line) - 1]
        return line

    def remove_telnet_chars(self, line):
        # Removes \r, \n, and various other things that may cause issues
        #   during sending/receiving of lines, like \x03
        line = line.replace("\r", "").replace("\n", "")
        for character in decoding_table:
            # Convert characters into readable hex string, like \x03 or \u201c
            character_readable = self.string_to_bytes_to_string(character)
            if character_readable.startswith('\\u') or character_readable.startswith('\\x'):
                # Remove front slashes since encoding messes them up. Re-add slashes later.
                line = line.replace(character, "")
        return line

    def run(self):
        # -------------------------
        # Main function of program.
        # -------------------------
        # Select backup config file from disk
        self.config_file_selection()
        # Do a telnet connection to device
        self.telnet_to_device()
        # Send/receive commands over telnet
        self.interact_with_device()


TeleCisc().run()
