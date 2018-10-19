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
CONFIGS_ROOT_DIR = ""
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

    def __init__(self):
        super().__init__()
        self.tele_instance = TeleCisco()
        self.tele_instance.configs_root_dir = CONFIGS_ROOT_DIR
        self.initialize()
        self.main_menu()

    def new_connection(self):
        self.tele_instance.reset()
        self.tele_instance.telnet_to_device()

    def initialize(self):
        print("Clearing any existing connections...")
        self.tele_instance.reset()  # Ensure it's fresh
        self.tele_instance.configs_root_dir = CONFIGS_ROOT_DIR
        self.config_file_selection()
        self.tele_instance.telnet_to_device()
        self.tele_instance.ios_login_and_elevate()

    def main_menu(self):

        menu = {
            1: self.initialize,
            2: self.compare_submenu,
            3: self.view_submenu,
            4: self.update_submenu,
        }
        while True:
            connection_status_msg = "Connection: " + (("Connected to " + self.tele_instance.host + ".") if self.tele_instance.connection else "No Connection Active.")
            connection_status_msg += "\n    - Selected file: '" + self.tele_instance.config_file_path + self.tele_instance.config_file_name + "'."
            selected_option = self.get_menu("MAIN",
            [
                connection_status_msg,
                "Compare Configurations.",
                "View Configurations.",
                "Update & Replace Configurations"
            ],
            "*Enter a value or [q]uit.\n>>>")
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

    def view_temp_file(self):
        self.divider()
        config_as_list = self.tele_instance.ios_fetch_and_store_conf(self.tele_instance.TEMP_FILE_NAME, "more")
        print("\n".join(config_as_list))
        self.divider()
        host_name = find_single_line_value(config_as_list, "hostname")
        print("\nHOSTNAME: " + host_name if host_name else "(Hostname not found in file)")

    def view_selected_file(self):
        # Does not re-read from a local file. Need to re-select a local file to get new changes.
        self.divider()
        print("\n".join(self.tele_instance.config_file))
        self.divider()

    def view_run(self):
        self.divider()
        print("\n".join(self.tele_instance.ios_fetch_and_store_conf("running-config", "show")))
        self.divider()

    def view_startup(self):
        self.divider()
        print("\n".join(self.tele_instance.ios_fetch_and_store_conf("startup-config", "show")))
        self.divider()

    def view_submenu(self):
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
        def cpy_running():
            self.tele_instance.ios_tclsh()
            self.view_temp_file()
            if input("\n*Try to copy this config to the running-config? [y/n]:").strip().lower() in ['y', 'yes']:
                self.tele_instance.ios_copy_to_config(self.tele_instance.TEMP_FILE_NAME, "running-config")
            self.tele_instance.ios_remove_temp_file()

        def cpy_startup():
            self.tele_instance.ios_tclsh()
            self.view_temp_file()
            if input("\n*Try to copy this config to the startup-config? [y/n]:").strip().lower() in ['y', 'yes']:
                self.tele_instance.ios_copy_to_config(self.tele_instance.TEMP_FILE_NAME, "startup-config")
            self.tele_instance.ios_remove_temp_file()

        def cpy_startup_to_run():
            if input("\n*Copy the startup-config to the running-config? [y/n]:").strip().lower() in ['y', 'yes']:
                self.tele_instance.ios_copy_to_config("startup-config", "running-config")

        def init_reload():
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
        current_running = self.tele_instance.ios_fetch_and_store_conf("running-config", "show")
        current_startup = self.tele_instance.ios_fetch_and_store_conf("startup-config", "show")
        # Compare running-config to selected file
        # Compare startup-config to selected file
        # Compare running-config to startup-config
        menu = {
            1: "asdf",
            2: "asdf",
            3: "asdf"
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
        host_name = find_single_line_value(config_as_list, "hostname")
        passwd = find_single_line_value(config_as_list, "password")
        username = find_single_line_value(config_as_list, "username")
        print(
            "\nPATH: " + abs_path + file_name + "\nHOSTNAME: " + host_name if host_name else "(Hostname not found in file)")
        good_file = input("\n*Continue using this file? [y/n]:")
        if good_file.strip().lower() in ["y", "yes"]:
            self.tele_instance.config_file = config_as_list
            self.tele_instance.config_file_path = abs_path
            self.tele_instance.config_file_name = file_name
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
            return True
        else:
            return False

    def config_file_selection(self):
        # Display menu, prompt for file selection. Get config
        print("\n---Configuration File Selection---")
        if not self.tele_instance.configs_root_dir:
            print("***Change CONFIGS_ROOT_DIR in the script to a config file location!***")
            self.tele_instance.configs_root_dir = input(
                "Enter an absolute path to a config file repository or a config file itself:")
        use_this_file = False
        while not use_this_file:
            try:
                if os.path.isdir(self.tele_instance.configs_root_dir):
                    abs_path, file_name = Menu().get_path_menu(self.tele_instance.configs_root_dir)
                    self.tele_instance.configs_root_dir = abs_path  # Move dir path here, in case user decides not to use file
                else:
                    abs_path = os.path.abspath(self.tele_instance.configs_root_dir)
                    file_name = abs_path[abs_path.rfind("\\") + 1:]
                    abs_path = abs_path.replace(file_name, "")
                    self.tele_instance.configs_root_dir = abs_path  # Move dir path here, in case user decides not to use file
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
            use_this_file = self.config_file_selection_prompts(local_config, abs_path, file_name)
        print("\nFile Selected!")


UserMenu()
