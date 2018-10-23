from telnetlib import Telnet
import getpass
import socket
from encodings.cp1252 import decoding_table


def string_to_bytes_to_string(line, encoding='utf-8'):
    # Hacky way to make characters recognizable and replaceable:
    # Convert to bytes object with utf-8 encoding
    # Make it a (bytes) string: b'some string'
    # Splice string to remove the b''
    line = bytes(line, encoding=encoding, errors='ignore')
    line = str(line)
    line = line[2:len(line) - 1]
    return line


def remove_telnet_chars(line):
    # Removes \r, \n, and various other things that may cause issues
    #   during sending/receiving of lines, like \x03
    line = line.replace("\r", "").replace("\n", "")
    for character in decoding_table:
        # Convert characters into readable hex string, like \x03 or \u201c
        character_readable = string_to_bytes_to_string(character)
        if character_readable.startswith('\\u') or character_readable.startswith('\\x'):
            # Remove front slashes since encoding messes them up. Re-add slashes later.
            line = line.replace(character, "")
    return line


class TeleCisco:
    PORT = 23
    TELNET_DEBUG_MODE = False
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
        self.config_file = []

    def ios_change_term_length(self, length):
        # Change terminal length to selected value. length = 0 is probably what you want.
        # Prevents --more-- prompt from showing, which causes issues with CRLFs
        print("Changing terminal length...")
        self.connection.write(("terminal length " + str(length)).encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work

    def ios_fetch_and_store_conf(self, file_name, view_command):
        # Read a file (file_name) using the view_command. Store every line of that file in store_list
        # view_command should be "more" for files in flash, and "show" for startup-config, running-config, etc.
        store_list = []
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
            if "Building" in line:
                # Fix occasional issue where it gets stuck on "Building Configuration..."
                self.connection.write("\r\n".encode("ascii") + b"\n")
                self.connection.read_until(b"\r\n", timeout=self.READ_TIMEOUT)
                continue
            if line.startswith(self.host + "#"):  # Lazy fix for occasional issue with commands being appended
                continue
            line = remove_telnet_chars(line)
            store_list.append(line)
        return store_list

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

    def input_username(self):
        while not self.username:
            self.username = input("Username: ")

    def input_host(self):
        while not self.host:
            self.host = input("IP or Hostname: ")

    def ios_login_and_elevate(self):
        # Get through username and password prompts and enter privileged mode.
        if not self.connection:
            print("Not connected to device! Attempting connection...")
            self.telnet_to_device()
            return
        print("\n---CLI Login---")
        while True:
            line = self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)
            if not line.strip():
                continue
            # LOGIN STUFF #
            if "Username:" in line.decode():
                self.input_username()
                self.connection.write(self.username.encode('ascii') + b"\n")
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
                print("Entered Privileged Mode!")
                break
            else:
                continue

    def ios_tclsh(self):
        # https://howdoesinternetwork.com/2018/create-file-cisco-ios
        # Deals with tcl shell to create a temporary text file
        # This file can then be copied to the startup-config
        # This is done instead of using the configuration mode, as we want to add a fresh config file and not
        #   have to worry about leftover settings being retained.
        if not self.connection:
            print("Not connected to device! Attempting connection...")
            self.telnet_to_device()
            return
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

    def ios_copy_to_config(self, config_to_copy_from, config_to_copy_to):
        # Use copy config to copy from one file to selected config file
        print("\n---Copying", config_to_copy_from, "to", config_to_copy_to + "---")
        self.connection.write(("copy " + config_to_copy_from + " " + config_to_copy_to).encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.write(config_to_copy_to.encode("ascii") + b"\n")
        # Get through all the copy prompts
        line = ""
        while "copied" not in line:
            line = self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
            line = line.decode()
        print(line)
        self.connection.write(b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work

    def ios_reload(self):
        # Reload OS so it uses the new config
        if not self.connection:
            print("Not connected to device! Attempting connection...")
            self.telnet_to_device()
            return
        print("\n---Reloading device---")
        self.connection.write("reload".encode("ascii") + b"\n")
        self.connection.read_until(b"\n", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
        while True:
            line = self.connection.read_until(b"\r", timeout=self.READ_TIMEOUT)  # Make written command work
            line = line.decode()
            if "no" in line:  # "[yes/no]" and "yes or no" telnet has a char limit per line sent.
                self.connection.write(b"yes\n")
                continue
            if "rm]" in line:  # [confirm]: - telnet has a char limit per line sent.
                self.connection.write(b"\r\n")
                break
            self.connection.write(b"\r\n")

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
        print("File deleted.")

    def reset(self):
        self.host = ""
        self.username = ""
        self.password = ""
        self.connection = None
        self.is_privileged_user = False

    def telnet_to_device(self):
        # Create telnet connection to host
        print("\n---Device Connection---")
        self.input_host()
        print("Attempting connection to " + self.host + "...")
        try:
            self.connection = Telnet(self.host, self.PORT, timeout=self.CONNECT_TIMEOUT)
            if self.TELNET_DEBUG_MODE:
                # Print extra console output
                self.connection.set_debuglevel(1)
        except (socket.gaierror, socket.timeout) as e:
            # Kill connection when it fails
            print("Connection to host failed:", e)
            self.connection = None
            return
        print("Connection Succeeded!")
