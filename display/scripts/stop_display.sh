#!/bin/bash
# beendet das Display/Touchscreen GUI
pkill -f '/usr/bin/X :0'
echo "Display gestoppt"
