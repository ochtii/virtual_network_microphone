#!/usr/bin/env python3
import os
import subprocess
import time
import json
import datetime
from pathlib import Path

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class AutoDeployer:
    def __init__(self, repo_path='/home/ochtii/gusch'):
        self.repo_path = Path(repo_path)
        self.last_commit = None
        self.monitored_extensions = {'.py', '.js', '.html', '.css', '.json', '.md', '.txt', '.sh'}
        
    def log(self, message, color=Colors.WHITE):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'{color}{Colors.BOLD}[{timestamp}]{Colors.END} {color}{message}{Colors.END}')
    
    def run_command(self, command, cwd=None):
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, '', 'Command timed out'
    
    def get_current_commit(self):
        success, stdout, stderr = self.run_command('git rev-parse HEAD')
        if success:
            return stdout.strip()
        return None
    
    def check_for_updates(self):
        self.log(' Checking for updates...', Colors.CYAN)
        
        # Force fetch latest changes with prune
        success, stdout, stderr = self.run_command('git fetch origin --force --prune')
        if not success:
            self.log(f' Failed to fetch: {stderr}', Colors.RED)
            # Fallback: try basic fetch
            success, stdout, stderr = self.run_command('git fetch origin')
            if not success:
                self.log(f' Fallback fetch also failed: {stderr}', Colors.RED)
                return False
        
        # Get remote commit
        success, remote_commit, stderr = self.run_command('git rev-parse origin/live')
        if not success:
            self.log(f' Failed to get remote commit: {stderr}', Colors.RED)
            return False
        
        current_commit = self.get_current_commit()
        
        if current_commit != remote_commit.strip():
            self.log(f' New changes detected!', Colors.GREEN)
            self.log(f'   Current: {current_commit[:8]}', Colors.YELLOW)
            self.log(f'   Remote:  {remote_commit.strip()[:8]}', Colors.GREEN)
            return True
        
        return False
    
    def show_diff(self):
        self.log(' Changes:', Colors.MAGENTA)
        
        # Get list of changed files
        success, files_output, stderr = self.run_command('git diff --name-only HEAD origin/live')
        if success and files_output.strip():
            changed_files = files_output.strip().split('\n')
            
            for file in changed_files:
                if any(file.endswith(ext) for ext in self.monitored_extensions):
                    self.log(f'    {file}', Colors.BLUE)
                    
                    # Show detailed diff for the file
                    success, diff_output, stderr = self.run_command(f'git diff HEAD origin/live -- {file}')
                    if success and diff_output:
                        lines = diff_output.split('\n')
                        for line in lines[:50]:  # Limit output
                            if line.startswith('+') and not line.startswith('+++'):
                                self.log(f'     {line}', Colors.GREEN)
                            elif line.startswith('-') and not line.startswith('---'):
                                self.log(f'     {line}', Colors.RED)
                            elif line.startswith('@@'):
                                self.log(f'     {line}', Colors.CYAN)
    
    def deploy(self):
        self.log(' Starting deployment...', Colors.GREEN)
        
        # Show what changes we're deploying
        self.show_diff()
        
        # Stash any local changes as fallback
        self.log(' Stashing any local changes...', Colors.YELLOW)
        self.run_command('git stash push -m "auto-deploy-backup-$(date +%Y%m%d-%H%M%S)"')
        
        # Force reset to clean state first
        self.log(' Resetting to clean state...', Colors.BLUE)
        success, stdout, stderr = self.run_command('git reset --hard HEAD')
        if not success:
            self.log(f' Failed to reset: {stderr}', Colors.RED)
        
        # Clean untracked files as fallback
        self.run_command('git clean -fd')
        
        # Force pull latest changes with reset
        success, stdout, stderr = self.run_command('git reset --hard origin/live')
        if not success:
            self.log(f' Failed to reset to origin/live: {stderr}', Colors.RED)
            # Fallback: try regular pull with force
            success, stdout, stderr = self.run_command('git pull origin live --force')
            if not success:
                self.log(f' Failed to pull with force: {stderr}', Colors.RED)
                # Last fallback: restore from stash if possible
                self.log(' Attempting to restore from stash...', Colors.YELLOW)
                self.run_command('git stash pop')
                return False
        
        self.log(' Code updated successfully', Colors.GREEN)
        
        # Check if requirements.txt changed
        success, stdout, stderr = self.run_command('git diff --name-only HEAD@{1} HEAD | grep requirements.txt')
        if success and stdout.strip():
            self.log(' Installing updated dependencies...', Colors.YELLOW)
            success, stdout, stderr = self.run_command('pip3 install -r requirements.txt')
            if not success:
                self.log(f'  Dependency installation warning: {stderr}', Colors.YELLOW)
        
        # Restart the application with PM2
        self.log(' Restarting application...', Colors.BLUE)
        success, stdout, stderr = self.run_command('~/.nvm/versions/node/v22.19.0/bin/pm2 reload ecosystem.config.js')
        
        if success:
            self.log(' Application restarted successfully', Colors.GREEN)
            self.log(' Deployment completed!', Colors.MAGENTA)
            return True
        else:
            self.log(f' Failed to restart application: {stderr}', Colors.RED)
            return False
    
    def run(self):
        self.log(' Auto-Deployment System Starting...', Colors.BOLD + Colors.GREEN)
        self.log(f' Monitoring: {self.repo_path}', Colors.CYAN)
        self.log(f'  Check interval: 5 seconds', Colors.CYAN)
        self.log(f' Branch: live', Colors.CYAN)
        self.log('=' * 50, Colors.WHITE)
        
        # Initial commit check
        self.last_commit = self.get_current_commit()
        if self.last_commit:
            self.log(f' Current commit: {self.last_commit[:8]}', Colors.YELLOW)
        
        while True:
            try:
                if self.check_for_updates():
                    if self.deploy():
                        self.last_commit = self.get_current_commit()
                    else:
                        self.log(' Deployment failed, will retry next cycle', Colors.RED)
                else:
                    # Minimal output when no changes
                    print('.', end='', flush=True)
                
                time.sleep(5)
                
            except KeyboardInterrupt:
                self.log('\\n Auto-deployment stopped by user', Colors.YELLOW)
                break
            except Exception as e:
                self.log(f' Unexpected error: {e}', Colors.RED)
                time.sleep(5)

if __name__ == '__main__':
    deployer = AutoDeployer()
    deployer.run()
