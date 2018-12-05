# ciscoTelneter
Script to simplify older Cisco switch/router config flashing without tftp. Telnet must be enabled on the recieving device, and there must be a working connection to said device.

This is used for Cisco switches and routers running IOS 12.X - this script may not work right with newer or older versions, and I don't have a way to test this either. This script is likely to break if there's much variation in commands between IOS versions.

It uses telnet, so it's not secure. It's intended to be used in a setting where switch and router security are not major concerns, such as an isolated student networking lab.  

**Features:**

 * Upload configs to your Cisco device without TFTP with a telnet connection. This script creates a temporary text file on the device using the Tcl shell, then copies that file to either the `running-config` or the `startup-config`.
 * Save configs to your local machine without TFTP.
 * View a device's config files.
 * List out and compare differences between the `running-config`, `startup-config`, and the selected backup config.
 * Switch into the device's command line if needed.
 * And more!
 
**Limitations:**

* Won't work when telnet is disabled on the device.
* Won't work when the device cannot be accessed remotely.
* Security is non-existant over telnet. Don't enter your login credentials if security is a concern.
* May not work with future/older versions of IOS.
* Won't work on IOS devices that don't support Tcl (like ASA firewalls).
* Can copy bad configs if you're not careful. Pay attention to the confirmation prompts.

**To run:** 

1. Put the directory to start looking for config files (or the config file path itself) in the `DEFAULT_CONFIGS_LOCATION` variable in `main.py`. If you don't, you'll be prompted to enter a path upon running the program. A small CLI interface will let you navigate directories and select the config file you want to use if a directory is entered.
2. Point Python 3 at the script and run: `python /path/to/main.py`

**Interface:**
```
------------------MAIN------------------
[1] - Restart with New File & Host.
[2] - Connected Host: router1
[3] - Using Config File: \\Server\Repos\Configs\router1\router1-confg
[4] - View Configs.
[5] - Compare Configs.
[6] - Save Configs.
[7] - Update Device Configs.
[8] - Switch to Device CLI.
----------------------------------------
*Enter a value or [q]uit.
>>>
```
* To navigate, enter the number for the menu option you want to select and press enter.
* Enter an 'r' to exit submenus and return to the main menu shown above.
* Enter a 'q' to exit the program.
* If you switch to the device command line, you will be unable to return to the the main interface unless you restart the script.
