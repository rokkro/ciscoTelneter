# ciscoTelneter
Script to simplify older Cisco switch/router config flashing without tftp. Telnet must be enabled on the recieving device, and there must be a working connection to said device. This script doesn't do console port connections (yet?).

This is used for Cisco switches and routers running IOS 12.X - this script probably won't work right with newer or older versions. This script is prone to breakage because of how different devices work.

It uses telnet, so it's not secure. It's intended to be used in a setting where switch and router security are not major concerns, such as an isolated student networking lab.  

To use: 

1. Put the directory to start looking for config files in the CONFIGS_ROOT_DIR variable. Upon running the script, a small CLI interface will let you navigate directories and select the config file you want to use.
2. Point Python 3 at the script and run.
