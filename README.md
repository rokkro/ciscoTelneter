# ciscoTelneter
Script to simplify older Cisco switch/router config flashing without tftp. Telnet must be enabled on the recieving device, and there must be a working connection to said device.

This is used for Cisco switches and routers running IOS 12.X - this script may not work right with newer or older versions, and I don't have a way to test this either. This script is likely to break if there's much variation in commands between IOS versions.

It uses telnet, so it's not secure. It's intended to be used in a setting where switch and router security are not major concerns, such as an isolated student networking lab.  

**Features:**

 * Skip using TFTP to upload configurations to the device. Only a telnet connection is needed. This script creates a temporary text file on the device using the Tcl shell, then copies that file to either the `running-config` or the `startup-config`.
 * View the contents of the `running-config` and the `startup-config` from the device the script has a telnet connection to.
 * List out and compare differences between the `running-config`, `startup-config`, and the selected backup config.
 * Copy the `startup-config` to the `running-config`.
 * Reload the device if desired.
 * Switch into the device's command line if needed.
 
 
**Limitations:**

* Won't work when telnet is disabled on the device.
* Won't work when the device cannot be accessed remotely.
* Security is poor over telnet. Don't use this script in environments where security is a concern.
* May not work with future/older versions of IOS.
* Won't work on IOS devices that don't support Tcl (like ASA firewalls).
* Can copy bad configs if you're not careful. Pay attention to the confirmation prompts.
* The password prompt won't show if running the script in PyCharm (it does show in PyCharm's debug mode, however).

**To run:** 

1. Put the directory to start looking for config files (or the config file itself) in the `CONFIGS_LOCATION` variable in `main.py`, otherwise you'll be prompted to upon running the program. A small CLI interface will let you navigate directories and select the config file you want to use if a directory is entered.
2. Point Python 3 at the script and run: `python /path/to/main.py`

**Interface:**
```
------------------MAIN------------------
[1] - Connection: Connected to router1.
    - Selected file: '\\Server\Cisco Configs\router\router1-confg'.
[2] - Compare Configurations.
[3] - View Configurations.
[4] - Update & Replace Configurations.
[5] - Switch to Device Command Line.
----------------------------------------
*Enter a value or [q]uit.
>>>
```
* To navigate, enter the number of the menu option you want to select and press enter.
* Entering a '1' in this menu will  both reset the connection and prompt you to select a config file again.
* Enter an 'r' to exit submenus and return to the main menu shown above.
* Enter a 'q' to exit the program.
* If you switch to the device command line, you will be unable to return to the above interface unless you restart the script.
