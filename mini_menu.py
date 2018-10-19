import os


class Menu:
    # Mini menu UI for selecting a file to use
    horizontal_len = 40
    input_queue = []

    def divider(self):  # ----------
        print('-' * self.horizontal_len)

    def header(self, text):  # ---header text---
        print(('-' * int((self.horizontal_len - len(text)) / 2)) + text + (
                    '-' * int((self.horizontal_len - len(text)) / 2)))

    def print_menu(self, head, menu):
        # Print menu, entries, divider
        self.header(head)
        for num, entry in enumerate(menu):  # Print entries
            print("[" + str(num + 1) + "] - " + str(entry))
        self.divider()

    def update_input_queue(self, input_menu):
        # Handle keys in queue
        if not self.input_queue:
            # Stylize input menu
            entry = input(input_menu.strip())
            if len(entry.split(" ")) > 1:
                entries = entry.split(" ")
                entry = entries[0]
                del entries[0]
                self.input_queue.extend(entries)
        else:
            entry = self.input_queue[0]
            del self.input_queue[0]
        return entry

    @staticmethod
    def handle_special_input(current_input):
        if current_input == 'q':  # input 'q' to quit
            quit(0)
        elif current_input == '' or current_input == 'r':  # Returns space/'r' for menus to handle it.
            return current_input
        else:
            return None

    def get_menu(self, head, menu, input_menu):
        # Numbered user input menu
        while True:
            # If no menu entries, don't do anything
            if not menu:
                print("There doesn't appear to be anything here...")
                return ''

            self.print_menu(head, menu)
            current_input = self.update_input_queue(input_menu)

            special_key = self.handle_special_input(current_input)
            if special_key is not None:
                return special_key

            # Verify normal input is a number value
            try:  # Type cast num input to int
                current_input = int(current_input)
            except ValueError:
                continue

            # Ensure number input falls within menu option range
            if ((current_input > len(menu)) if menu is not None else False) or current_input < 1:
                continue  # Recognize as invalid input
            return current_input  # Successfully return numbered input for menus to handle

    @staticmethod
    def gen_file_menu(files):
        # Appending a "/" to dir names here so it's easy to differentiate between files and dirs in the menu UI.
        menu_display = []
        for file in files:
            if os.path.isdir("./" + file):
                # If dir, show visual indicator for how many files inside it
                menu_display.append(file + "/\t->(" + str(len(os.listdir("./" + file))) + ")")
            else:
                menu_display.append(file)
        return menu_display

    def get_path_menu(self, path="./"):
        """
        Saves original working dir in cwd. Gets abs path of input dir, and changes to it.
          Creates menu from that dir. If ENTER is pressed, go up a dir. If a dir is selected, change to it.
          Rinse and Repeat. Convert final file path to abspath, and cut out file name from it. Change to original cwd.
          Return absolute path and the file name (strings).
        """
        cwd = os.getcwd()
        path = os.path.abspath(path)
        os.chdir(path)  # Change dir to path param
        while True:
            files = os.listdir("./")  # List files in current dir
            menu_display = self.gen_file_menu(files)
            user_input = self.get_menu(path, menu_display, "*Enter a file/dir number or [Enter] - go up a dir.\n>>>")
            if user_input == '' or user_input == 'r':  # Go up a dir if input is empty/'r'
                os.chdir("..")
                continue
            selected = files[user_input - 1]
            if os.path.isdir("./" + selected):
                os.chdir(selected)
                continue
            selected_file = selected
            break
        file_abs = os.path.abspath(selected_file).replace(selected_file, "")  # Get the abs path without the file
        os.chdir(cwd)  # Change cwd back to what it was before
        return file_abs, selected_file
