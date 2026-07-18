#!/usr/bin/env python3
"""
Keylogger Plugin - Module untuk keylogging
"""

import time
import threading
import os
from typing import Dict

# Import module system
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.module_system import Module


class KeyloggerPlugin(Module):
    """Keylogger plugin"""
    
    def __init__(self):
        self.running = False
        self.log_file = None
        self.keys = []
    
    def get_name(self) -> str:
        return "keylogger"
    
    def get_description(self) -> str:
        return "Keylogger module untuk capture keystrokes"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def init(self) -> bool:
        self.log_file = os.path.expanduser("~/.keylog.txt")
        return True
    
    def cleanup(self) -> bool:
        self.running = False
        return True
    
    def start_capture(self):
        """Start key capture"""
        self.running = True
        while self.running:
            # In production, would use actual keylogger
            # For demo, simulate
            time.sleep(1)
    
    def execute(self, args: Dict) -> Dict:
        action = args.get('action', 'start')
        
        if action == 'start':
            if not self.running:
                thread = threading.Thread(target=self.start_capture, daemon=True)
                thread.start()
                return {'success': True, 'message': 'Keylogger started'}
        elif action == 'stop':
            self.running = False
            return {'success': True, 'message': 'Keylogger stopped'}
        elif action == 'get_logs':
            try:
                with open(self.log_file, 'r') as f:
                    logs = f.read()
                return {'success': True, 'logs': logs}
            except:
                return {'success': True, 'logs': 'No logs yet'}
        
        return {'success': False, 'error': f'Unknown action: {action}'}
