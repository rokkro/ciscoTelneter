# DO NOT USE THIS SCRIPT IN PLACES WHERE SECURITY IS IMPORTANT! Telnet is NOT a secure protocol.
# This script is used in an isolated student/education environment.
# It serves as a simple way for a lab assistant to reset device configurations after students do lab assignments.
# Used for resetting Cisco IOS 12.X switches/routers.
# Running this in an IDE will probably not display the password prompt, given how getpass() works.

from mini_menu import Menu
from telnet_device import TeleCisco, remove_telnet_chars
import os, uuid

##################################################################
# PUT THE STARTING DIRECTORY FOR LOCATING CONFIG FILES HERE
# You have to use forward slashes instead of backslashes on Windows
DEFAULT_CONFIGS_LOCATION = ""
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
        self.configs_location = DEFAULT_CONFIGS_LOCATION
        self.config_file_path = ""
        self.config_file_name = ""
        self.config_file_selection()
        self.main_menu()

    def change_conf_file(self):
        self.configs_location = ""
        self.config_file_path = ""
        self.config_file_name = ""
        self.config_file_selection()

    def host_connect(self):
        try:
            if self.tele_instance.connection:
                self.tele_instance.username = ""
                self.tele_instance.password = ""
                self.tele_instance.connection = None
                self.tele_instance.is_privileged_user = False
            self.tele_instance.telnet_to_device()
            self.tele_instance.ios_login_and_elevate()
        except EOFError as e:
            # Connection probably terminated.
            print(e)

    def new_host_connection(self):
        self.tele_instance.host = ""
        self.host_connect()

    @staticmethod
    def get_path():
        path = ""
        while True:
            path = input("Enter a path to the directory to save the config in, excluding the file name:")
            path = path.replace("\\\\", "\\")
            if not os.path.isdir(path):
                print("Invalid directory path!")
                continue
            try:  # Test write permissions of the directory
                print("Testing write permissions...")
                path_to_file = path + "/" + str(uuid.uuid4())
                with open(path_to_file,'w') as test_file:
                    test_file.write("test")
                os.remove(path_to_file)
            except Exception as e:
                print("Write issue:",e)
            else:
                break
        return path

    def save_config(self, config_name):
        config_list = self.tele_instance.ios_fetch_and_store_conf(config_name, "show")
        print("(The file should be displayed below if no errors occurred).")
        self.divider()
        print("\n".join(i for i in config_list))
        self.divider()
        inpt = input("Save the above config? [y/n]:")
        if inpt.strip().lower() in ['n', 'no']:
            return
        path = self.get_path()
        unique_path = path + "/" + config_name + "-" + str(uuid.uuid4())  # Random uuid at end to make it unique
        with open(unique_path, 'w') as file_to_write_to:
            for line in config_list:
                file_to_write_to.write(line + "\n")
            print("Saved at: " + unique_path)

    def save_submenu(self):
        def save_running():
            self.save_config("running-config")

        def save_startup():
            self.save_config("startup-config")

        menu = {
            1: save_running,
            2: save_startup,
        }
        while True:
            selected_option = self.get_menu("SAVE",
            [
                "Save Current running-config to Local Machine.",
                "Save Current startup-config to Local Machine."
            ],
            "*Enter a value or [r]return, [q]uit.\n>>>")
            if selected_option == 'r':
                return
            if not selected_option:
                continue
            try:
                menu[selected_option]()
            except KeyError:
                pass
            except (ConnectionAbortedError, EOFError) as e:
                self.tele_instance.connection = None
                print("\n", e)

    def start_over(self):
        self.tele_instance.host = ""
        self.tele_instance.username = ""
        self.tele_instance.password = ""
        self.tele_instance.connection = None
        self.tele_instance.is_privileged_user = False
        self.config_file_selection()

    def main_menu(self):
        # Displays main menu and gets user input
        menu = {
            1: self.start_over,
            2: self.new_host_connection,
            3: self.change_conf_file,
            4: self.view_submenu,
            5: self.compare_submenu,
            6: self.save_submenu,
            7: self.update_submenu,
            8: self.switch_to_cli
        }
        while True:
            path_display = self.config_file_path + self.config_file_name
            selected_option = self.get_menu("MAIN",
            [
                "Restart with New File & Host.",
                "Connected Host: " + (self.tele_instance.host if (self.tele_instance.host and self.tele_instance.connection) else "(NOT CONNECTED)"),
                "Using Config File: " + (path_display if path_display.strip() else "(NO PATH SELECTED)"),
                "View Configs.",
                "Compare Configs.",
                "Save Configs.",
                "Update Device Configs.",
                "Switch to Device CLI.",
            ],
            "*Enter a value or [q]uit.\n>>>",False)
            if selected_option == 'r':
                continue
            if not selected_option:
                continue
            try:
                menu[selected_option]()
            except KeyError:
                pass
            except (ConnectionAbortedError, EOFError, AttributeError) as e:
                self.tele_instance.connection = None
                print("\n", e)

    def view_temp_file(self):
        # Print out contents of temporary file stored on device.
        # This file is later deleted from the device after copying.
        config_as_list = self.tele_instance.ios_fetch_and_store_conf(self.tele_instance.TEMP_FILE_NAME, "more")
        if not config_as_list:
            print("Config file was either empty, not found, or not read properly.")
            return True  # Indicate not safe to copy
        print("(The file should be displayed below if no errors occurred).")
        self.divider()
        print("\n".join(config_as_list))
        self.divider()
        host_name = find_single_line_value(config_as_list, "hostname")
        print("\nHOSTNAME: " + host_name if host_name else "(Hostname not found in file)")

    def view_selected_file(self):
        # Prints content of selected local config file.
        # Does not re-read from a local file, as it's stored as a list.
        if not self.tele_instance.config_file:
            print("No config file selected...")
            return
        print("(The file should be displayed below if no errors occurred).")
        self.divider()
        print("\n".join(self.tele_instance.config_file))
        self.divider()

    def switch_to_cli(self):
        print("Switching to command line. You will not be able to return to the program unless you restart it.\n"
              "Press Enter several times to see the command line.")
        self.tele_instance.connection.interact()

    def view_run(self):
        # Prints out content of device's current running-config
        config = "\n".join(self.tele_instance.ios_fetch_and_store_conf("running-config", "show"))
        print("(The file should be displayed below if no errors occurred).")
        self.divider()
        print(config)
        self.divider()

    def view_startup(self):
        # Prints out content of device's current startup-config
        config = "\n".join(self.tele_instance.ios_fetch_and_store_conf("startup-config", "show"))
        print("(The file should be displayed below if no errors occurred).")
        self.divider()
        print(config)
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
                  "View Local Config."
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
            if self.view_temp_file():
                print("Copy operation canceled.")
                return  # If temp file viewer indicated it's not safe to copy, then return instead
            if input("\n*Try to copy this config to the running-config? [y/n]:").strip().lower() in ['y', 'yes']:
                self.tele_instance.ios_copy_to_config(self.tele_instance.TEMP_FILE_NAME, "running-config")
            self.tele_instance.ios_remove_temp_file()

        def cpy_startup():
            # Tells device to copy the local config to the device as a temp file, then copy it to startup-config
            self.tele_instance.ios_tclsh()
            if self.view_temp_file():
                print("Copy operation canceled.")
                return  # If temp file viewer indicated it's not safe to copy, then return instead
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
                  "Copy Local Config to running-config.",
                  "Copy Local Config to startup-config.",
                  "Copy startup-config to running-config.",
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

        def list_difference(list_1, list_2, list_1_name, list_2_name):
            # Shows differences of both lists
            # Field size surrounding file name label
            name_spacing = (len(list_1_name)) if len(list_1_name) > len(list_2_name) else (len(list_2_name))
            diff_list_1 = []
            diff_list_2 = []

            for line_no, list_1_element in enumerate(list_1):
                if list_1_element.strip() and list_1_element not in list_2:
                    diff_list_1.append(str(line_no + 1).ljust(5,' ') + list_1_name.ljust(name_spacing,' ') + ": " + list_1_element)
            for line_no, list_2_element in enumerate(list_2):
                if list_2_element.strip() and list_2_element not in list_1:
                    diff_list_2.append(str(line_no + 1).ljust(5,' ') + list_2_name.ljust(name_spacing,' ') + ": " + list_2_element)
            return diff_list_1, diff_list_2

        def format_list_diffs(list_1, list_2, file_name_1, file_name_2):
            # For printing diff lists nicely
            diff_list_1, diff_list_2 = list_difference(list_1, list_2, file_name_1, file_name_2)
            print("\n\n")  # Jump a couple lines to reduce immediate clutter
            self.divider()
            print("Lines in " + file_name_1 + ", but not in " + file_name_2 + ":")
            self.divider()
            print("\n".join(diff_list_1))
            print("\n", end='')
            self.divider()
            print("Lines in " + file_name_2 + ", but not in " + file_name_1 + ":")
            self.divider()
            print("\n".join(diff_list_2))
            print("\n", end='')
            self.divider()

        def run_vs_startup():
            # Prints out differences between these files, separated by line.
            format_list_diffs(current_running,current_startup,"running-config", "startup-config")

        def run_vs_selected():
            # Prints out differences between these files, separated by line.
            local_conf_name = "(local config)"
            format_list_diffs(current_running, self.tele_instance.config_file, "running-config",local_conf_name)

        def startup_vs_selected():
            # Prints out differences between these files, separated by line.
            local_conf_name = "(local config)"
            format_list_diffs(current_startup, self.tele_instance.config_file, "startup-config",local_conf_name)

        menu = {
            1: run_vs_selected,
            2: startup_vs_selected,
            3: run_vs_startup
        }
        while True:
            selected_option = Menu().get_menu("COMPARE",
              [
                  "Compare running-config to Local Config.",
                  "Compare startup-config to Local Config.",
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
        self.tele_instance.password = find_single_line_value(config_as_list, "password")  # Find "password" field in file
        self.tele_instance.username = find_single_line_value(config_as_list, "username")  # Find "username" field in file

        print("\nPATH: " + abs_path + file_name)
        print("HOSTNAME: " + host_name if host_name else "(Hostname not found in file)")

        user_approval = input("\n*Continue using this file? [y/n]:")
        if user_approval.strip().lower() in ["y", "yes"]:
            self.tele_instance.config_file = config_as_list
            self.config_file_path = abs_path
            self.config_file_name = file_name
            if host_name:
                use_this_host = input("\n*Attempt to connect using the hostname '" + host_name + "'? [y/n]:")
                if use_this_host.strip().lower() in ["y", "yes"]:
                    self.tele_instance.host = host_name
                    self.host_connect()
                elif not self.tele_instance.connection:
                    self.new_host_connection()
            # Return True, indicating the user wants to use this file.
            return True
        else:
            return False

    def input_configs_location(self):
        # If user didn't specify DEFAULT_CONFIGS_LOCATION, prompt for it.
        if not self.configs_location:
            self.configs_location = \
                input("Enter an absolute path to a config file repository or a config file itself:")

    def config_file_selection(self):
        # Ensure user entered a file
        self.input_configs_location()
        # Keep displaying the menu until the user decides on a file
        use_this_file = False
        while not use_this_file:
            try:
                # If DEFAULT_CONFIGS_LOCATION is a directory, spawn a menu, else use that file
                if os.path.isdir(self.configs_location):
                    abs_path, file_name = Menu().get_path_menu(self.configs_location)
                    self.configs_location = abs_path  # Move dir path here, in case user decides not to use file
                else:
                    abs_path = os.path.abspath(self.configs_location)
                    file_name = abs_path[abs_path.rfind("\\") + 1:]
                    abs_path = abs_path.replace(file_name, "")
                    self.configs_location = abs_path  # Move dir path here, in case user decides not to use file
            except ValueError:
                return
            except Exception as e:
                print("Config path issue:", e, "\n")
                return
            # Remove CRLF without stripping spaces
            try:
                local_config = list(remove_telnet_chars(i) for i in open(abs_path + file_name))
            except (UnicodeDecodeError, OSError) as e:
                print("Bad path:", e)
                return
            except FileNotFoundError as e:
                print("File selected does not exist:", e)
                continue
            print("(The file should be displayed below if no errors occurred).")
            self.divider()
            print("\n".join(local_config))
            self.divider()
            # Ask user if they want to use the file + other prompts
            use_this_file = self.config_file_selection_prompts(local_config, abs_path, file_name)
        print("\nFile Selected!")


UserMenu()
