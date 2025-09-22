#!/bin/bash

echo  Starting Gusch Auto-Deployment System...
echo  Repository: https://github.com/ochtii/gusch.git
echo  Branch: live
echo  Sync interval: 5 seconds
echo "

cd /home/pi/gusch

# Make sure we are on the live branch
git checkout live

# Start the auto-deployment monitor
python3 auto-deploy.py
