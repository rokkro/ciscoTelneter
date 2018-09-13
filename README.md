# ciscoTelneter
Script to simplify older Cisco switch/router config flashing without tftp.

## WIP!

This uses Telnet, so it's not secure. It's intended to be used in a setting where switch and router security are not major concerns, such as an isolated student networking lab.  

To use: 

1. Put the directory to start looking for config files in the CONFIGS_ROOT_DIR variable. Upon running the script, a small CLI interface will let you navigate directories and select the config file you want to use.
2. Point Python 3 at the script and run.
