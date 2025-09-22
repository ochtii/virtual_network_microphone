#!/usr/bin/env python3
"""
PM2-kompatibles Deployment-Monitoring Script
Läuft als Daemon und prüft alle 5 Minuten auf Updates
"""

import time
import subprocess
import logging
import os
import sys

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def run_deployment():
    """Führt das Deployment-Script aus"""
    try:
        logging.info("Checking for GitHub updates...")
        
        result = subprocess.run(
            ['/bin/bash', '/home/ochtii/pimic/deploy.sh'],
            capture_output=True,
            text=True,
            timeout=300,  # 5 Minuten Timeout
            cwd='/home/ochtii/pimic'
        )
        
        if result.returncode == 0:
            logging.info("Deployment check completed successfully")
            if result.stdout:
                logging.info(f"Deploy output: {result.stdout.strip()}")
        else:
            logging.error(f"Deployment failed with code {result.returncode}")
            if result.stderr:
                logging.error(f"Deploy stderr: {result.stderr.strip()}")
                
    except subprocess.TimeoutExpired:
        logging.error("Deployment script timed out after 5 minutes")
    except Exception as e:
        logging.error(f"Deployment error: {e}")

def main():
    """Hauptschleife für kontinuierliches Monitoring"""
    logging.info("Starting GitHub deployment monitor...")
    logging.info("Checking for updates every 5 minutes...")
    
    # Erste Prüfung sofort
    run_deployment()
    
    # Dann alle 5 Minuten
    while True:
        try:
            time.sleep(300)  # 5 Minuten warten
            run_deployment()
            
        except KeyboardInterrupt:
            logging.info("Deployment monitor shutting down...")
            break
        except Exception as e:
            logging.error(f"Monitor error: {e}")
            time.sleep(60)  # Bei Fehlern nur 1 Minute warten

if __name__ == '__main__':
    main()