#!/bin/bash
# startet das Display/Touchscreen GUI
# z.B. Matchbox WM oder dein eigenes Programm
pkill -f '/usr/bin/X :0'
startx /home/ochtii/display/main_program &> /dev/null &
echo "Display gestartet"
