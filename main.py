# DO NOT USE THIS SCRIPT IN PLACES WHERE SECURITY IS IMPORTANT! Telnet is NOT a secure protocol.
# This script is used in an isolated student/education environment.
# It serves as a simple way for a lab assistant to reset device configurations after students do lab assignments.
# Used for resetting Cisco IOS 12.X switches/routers.
# Running this in an IDE will probably not display the password prompt, given how getpass() works.

from mini_menu import Menu
from telnet_device import TeleCisco, remove_telnet_chars
import os

##################################################################
# PUT THE STARTING DIRECTORY FOR LOCATING CONFIG FILES HERE
# You can use forward slashes instead of backslashes on Windows
CONFIGS_LOCATION = ""
##################################################################


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


class UserMenu(Menu):
    # Handles most user command line interaction. Creates menus, prompts for user input, etc.

    def __init__(self):
        # Initial device connection + selection stuff, then show menu interface
        super().__init__()
        self.tele_instance = TeleCisco()
        self.configs_location = CONFIGS_LOCATION
        self.config_file_path = ""
        self.config_file_name = ""
        self.initialize()
        self.main_menu()

    def initialize(self):
        # Clear connection, reprompt for file selection,
        #  connect to device, elevate privileges
        print("Clearing any existing connections...")
        try:
            self.tele_instance.reset()  # Ensure it's fresh
            self.config_file_selection()
            self.tele_instance.telnet_to_device()
            self.tele_instance.ios_login_and_elevate()
        except EOFError as e:
            # Connection probably terminated.
            print(e)

    def main_menu(self):
        # Displays main menu and gets user input
        menu = {
            1: self.initialize,
            2: self.compare_submenu,
            3: self.view_submenu,
            4: self.update_submenu,
            5: self.switch_to_commandline
        }
        while True:
            connection_status_msg = "Connection: " + (("Connected to " + self.tele_instance.host + ".")
                                        if self.tele_instance.connection else "No Connection Active.")
            connection_status_msg += "\n    - Selected file: '" + self.config_file_path + self.config_file_name + "'."
            selected_option = self.get_menu("MAIN",
            [
                connection_status_msg,
                "Compare Configurations.",
                "View Configurations.",
                "Update & Replace Configurations",
                "Switch to Device Command Line"
            ],
            "*Enter a value or [q]uit.\n>>>")
            if selected_option == 'r':
                continue
            if not selected_option:
                continue
            try:
                menu[selected_option]()
            except KeyError:
                pass
            except (ConnectionAbortedError, EOFError) as e:
                self.tele_instance.connection = None
                print("\n", e)

    def view_temp_file(self):
        # Print out contents of temporary file stored on device.
        # This file is later deleted from the device after copying.
        self.divider()
        config_as_list = self.tele_instance.ios_fetch_and_store_conf(self.tele_instance.TEMP_FILE_NAME, "more")
        print("\n".join(config_as_list))
        self.divider()
        host_name = find_single_line_value(config_as_list, "hostname")
        print("\nHOSTNAME: " + host_name if host_name else "(Hostname not found in file)")

    def view_selected_file(self):
        # Prints content of selected local config file.
        # Does not re-read from a local file, as it's stored as a list.
        self.divider()
        print("\n".join(self.tele_instance.config_file))
        self.divider()

    def switch_to_commandline(self):
        print("Switching to command line. You will not be able to return to the program unless you restart it.\n"
              "Press Enter several times to see the command line.")
        self.tele_instance.connection.interact()

    def view_run(self):
        # Prints out content of device's current running-config
        self.divider()
        print("\n".join(self.tele_instance.ios_fetch_and_store_conf("running-config", "show")))
        self.divider()

    def view_startup(self):
        # Prints out content of device's current startup-config
        self.divider()
        print("\n".join(self.tele_instance.ios_fetch_and_store_conf("startup-config", "show")))
        self.divider()

    def view_submenu(self):
        # Displays submenu for viewing files.
        menu = {
            1: self.view_run,
            2: self.view_startup,
            3: self.view_selected_file
        }

        while True:
            selected_option = Menu().get_menu("VIEW",
              [
                  "View running-config.",
                  "View startup-config.",
                  "View selected file."
              ],
              "*Enter a value or [r]eturn, [q]uit.\n>>>")
            if selected_option == 'r':
                return
            if not selected_option:
                continue
            try:
                menu[selected_option]()
            except KeyError:
                pass

    def update_submenu(self):
        # Displays submenu for copying/updating various files.

        def cpy_running():
            # Tells device to copy the local config to the device as a temp file, then copy it to running-config
            self.tele_instance.ios_tclsh()
            self.view_temp_file()
            if input("\n*Try to copy this config to the running-config? [y/n]:").strip().lower() in ['y', 'yes']:
                self.tele_instance.ios_copy_to_config(self.tele_instance.TEMP_FILE_NAME, "running-config")
            self.tele_instance.ios_remove_temp_file()

        def cpy_startup():
            # Tells device to copy the local config to the device as a temp file, then copy it to startup-config
            self.tele_instance.ios_tclsh()
            self.view_temp_file()
            if input("\n*Try to copy this config to the startup-config? [y/n]:").strip().lower() in ['y', 'yes']:
                self.tele_instance.ios_copy_to_config(self.tele_instance.TEMP_FILE_NAME, "startup-config")
            self.tele_instance.ios_remove_temp_file()

        def cpy_startup_to_run():
            # Tells device to copy the startup-config to the running-config
            if input("\n*Copy the startup-config to the running-config? [y/n]:").strip().lower() in ['y', 'yes']:
                self.tele_instance.ios_copy_to_config("startup-config", "running-config")

        def init_reload():
            # Tells device to reload, saving any changes made to the running-config
            if input("\n*Reload the device? The telnet connection will close. [y/n]:").strip().lower() in ['y', 'yes']:
                self.tele_instance.ios_reload()

        menu = {
            1: cpy_running,
            2: cpy_startup,
            3: cpy_startup_to_run,
            4: init_reload
        }
        while True:
            selected_option = Menu().get_menu("UPDATE",
              [
                  "Copy selected file to running-config.",
                  "Copy selected file to startup-config.",
                  "Copy startup-config to running-config",
                  "Reload the device.",
              ],
              "*Enter a value or [r]eturn, [q]uit.\n>>>")
            if selected_option == 'r':
                return
            if not selected_option:
                continue
            try:
                menu[selected_option]()
            except KeyError:
                pass

    def compare_submenu(self):
        # Displays menu for viewing differences between various files.
        # Gets the configs upon entering submenu, so they aren't reloaded constantly.
        # Comparison functionality is fairly basic at the moment.
        current_running = self.tele_instance.ios_fetch_and_store_conf("running-config", "show")
        current_startup = self.tele_instance.ios_fetch_and_store_conf("startup-config", "show")

        def list_difference(li1, li2):
            # Shows differences of both lists
            return list(set(li1) ^ set(li2))

        def run_vs_startup():
            # Prints out differences between these files, separated by line.
            print("Differences between running-config and startup-config.")
            self.divider()
            print("\n".join(list_difference(current_running, current_startup)))
            self.divider()

        def run_vs_selected():
            # Prints out differences between these files, separated by line.
            print("Differences between running-config and selected config.")
            self.divider()
            print("\n".join(list_difference(current_running, self.tele_instance.config_file)))
            self.divider()

        def startup_vs_selected():
            # Prints out differences between these files, separated by line.
            print("Differences between startup-config and selected config.")
            self.divider()
            print("\n".join(list_difference(current_startup, self.tele_instance.config_file)))
            self.divider()

        menu = {
            1: run_vs_selected,
            2: startup_vs_selected,
            3: run_vs_startup
        }
        while True:
            selected_option = Menu().get_menu("COMPARE",
              [
                  "Compare running-config to selected file.",
                  "Compare startup-config to selected file.",
                  "Compare running-config to startup-config."
              ],
              "*Enter a value or [r]eturn, [q]uit.\n>>>")
            if selected_option == 'r':
                return
            if not selected_option:
                continue
            try:
                menu[selected_option]()
            except KeyError:
                pass

    def config_file_selection_prompts(self, config_as_list, abs_path, file_name):
        # Prompt for whether or not file should be used. Prompt for usage of hostname or password from config file
        host_name = find_single_line_value(config_as_list, "hostname")  # Find "hostname" field in file
        passwd = find_single_line_value(config_as_list, "password")  # Find "password" field in file
        username = find_single_line_value(config_as_list, "username")  # Find "username" field in file

        print("\nPATH: " + abs_path + file_name)
        print("HOSTNAME: " + host_name if host_name else "(Hostname not found in file)")

        user_approval = input("\n*Continue using this file? [y/n]:")
        if user_approval.strip().lower() in ["y", "yes"]:
            self.tele_instance.config_file = config_as_list
            self.config_file_path = abs_path
            self.config_file_name = file_name
            if host_name:
                use_this_host = input("\n*Is the device currently using the hostname '" + host_name + "'? [y/n]:")
                if use_this_host.strip().lower() in ["y", "yes"]:
                    self.tele_instance.host = host_name
            if username:
                use_this_username = input(
                    "\n*Username '" + username + "' found in config. Use it for logging in? [y/n]:")
                if use_this_username.strip().lower() in ["y", "yes"]:
                    self.tele_instance.username = username
            if passwd:
                use_this_pass = input("\n*Password found as plaintext in config. Use it for logging in? [y/n]:")
                if use_this_pass.strip().lower() in ["y", "yes"]:
                    self.tele_instance.password = passwd

            # Return True, indicating the user wants to use this file.
            return True
        else:
            return False

    def input_configs_location(self):
        # If user didn't specify CONFIGS_LOCATION, prompt for it.
        if not self.configs_location:
            print("***Change CONFIGS_LOCATION in the script to a config file location!***")
            self.configs_location = \
                input("Enter an absolute path to a config file repository or a config file itself:")

    def config_file_selection(self):
        # Display menu, prompt for file selection.
        print("\n---Configuration File Selection---")
        # Ensure user entered a file
        self.input_configs_location()
        # Keep displaying the menu until the user decides on a file
        use_this_file = False
        while not use_this_file:
            try:
                # If CONFIGS_LOCATION is a directory, spawn a menu, else use that file
                if os.path.isdir(self.configs_location):
                    abs_path, file_name = Menu().get_path_menu(self.configs_location)
                    self.configs_location = abs_path  # Move dir path here, in case user decides not to use file
                else:
                    abs_path = os.path.abspath(self.configs_location)
                    file_name = abs_path[abs_path.rfind("\\") + 1:]
                    abs_path = abs_path.replace(file_name, "")
                    self.configs_location = abs_path  # Move dir path here, in case user decides not to use file
            except Exception as e:
                print("Config path issue:", e, "\nExiting...")
                quit()
            # Remove CRLF without stripping spaces
            try:
                local_config = list(remove_telnet_chars(i) for i in open(abs_path + file_name))
            except (UnicodeDecodeError, OSError) as e:
                print("Bad file selected:", e)
                continue
            except FileNotFoundError as e:
                print("File selected does not exist:", e)
                continue
            self.divider()
            print("\n".join(local_config))
            self.divider()
            # Ask user if they want to use the file + other prompts
            use_this_file = self.config_file_selection_prompts(local_config, abs_path, file_name)
        print("\nFile Selected!")


UserMenu()
