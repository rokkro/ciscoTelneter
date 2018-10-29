# ciscoTelneter
Script to simplify older Cisco switch/router config flashing without tftp. Telnet must be enabled on the recieving device, and there must be a working connection to said device.

This is used for Cisco switches and routers running IOS 12.X - this script probably won't work right with newer or older versions. This script is prone to breakage because of how different devices work.

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
* May not work with future versions of IOS or IOS devices that don't support Tcl (like ASA firewalls).
* Can copy bad configs if you're not careful. Pay attention to the confirmation prompts.

**To run:** 

1. Put the directory to start looking for config files (or the config file itself) in the CONFIGS_LOCATION variable, otherwise you'll be prompted to upon running the program. A small CLI interface will let you navigate directories and select the config file you want to use if a directory is entered.
2. Point Python 3 at the script and run: `python /path/to/main.py`
