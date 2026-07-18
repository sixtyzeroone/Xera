#!/usr/bin/env python3
"""
Module System - Extensible Plugin Architecture
Features: Dynamic loading, Plugin management, Hot-reload
"""

import importlib
import importlib.util
import inspect
import os
import sys
import json
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod
from pathlib import Path
import traceback


class Module(ABC):
    """Base module interface - semua module harus inherit dari class ini"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Module name"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Module description"""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """Module version"""
        pass
    
    @abstractmethod
    def execute(self, args: Dict) -> Dict:
        """Execute module with arguments"""
        pass
    
    @abstractmethod
    def init(self) -> bool:
        """Initialize module"""
        pass
    
    @abstractmethod
    def cleanup(self) -> bool:
        """Cleanup module"""
        pass
    
    def get_dependencies(self) -> List[str]:
        """Get module dependencies (optional)"""
        return []
    
    def get_commands(self) -> Dict[str, Callable]:
        """Get custom commands (optional)"""
        return {}
    
    def on_load(self):
        """Called when module is loaded"""
        pass
    
    def on_unload(self):
        """Called when module is unloaded"""
        pass


class ModuleManager:
    """Manage all modules - loading, unloading, executing"""
    
    def __init__(self, module_dir: str = "plugins"):
        self.module_dir = Path(module_dir)
        self.modules: Dict[str, Module] = {}
        self.module_states: Dict[str, Dict] = {}
        self.module_threads: Dict[str, threading.Thread] = {}
        self.running = True
        self.event_handlers: Dict[str, List] = {}
        
        # Create module directory if not exists
        self.module_dir.mkdir(exist_ok=True)
        
        # Load modules
        self.load_all_modules()
    
    def load_all_modules(self) -> int:
        """Load all modules from directory"""
        loaded = 0
        
        for file_path in self.module_dir.glob("*.py"):
            if file_path.name.startswith("_") or file_path.name == "__init__.py":
                continue
            
            module_name = file_path.stem
            
            try:
                if self.load_module(module_name):
                    loaded += 1
            except Exception as e:
                print(f"[-] Failed to load module {module_name}: {e}")
                traceback.print_exc()
        
        return loaded
    
    def load_module(self, module_name: str) -> bool:
        """Load a single module by name"""
        file_path = self.module_dir / f"{module_name}.py"
        
        if not file_path.exists():
            return False
        
        try:
            # Import module
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find Module classes
            for item_name in dir(module):
                item = getattr(module, item_name)
                if (inspect.isclass(item) and 
                    issubclass(item, Module) and 
                    item != Module):
                    
                    # Instantiate module
                    module_instance = item()
                    
                    # Check dependencies
                    deps = module_instance.get_dependencies()
                    for dep in deps:
                        if dep not in self.modules:
                            print(f"[!] Module {module_name} depends on {dep} but not loaded")
                            return False
                    
                    # Initialize
                    if module_instance.init():
                        self.modules[module_name] = module_instance
                        self.module_states[module_name] = {
                            'loaded': True,
                            'name': module_instance.get_name(),
                            'version': module_instance.get_version(),
                            'status': 'active',
                            'loaded_at': time.time()
                        }
                        module_instance.on_load()
                        print(f"[+] Loaded module: {module_name} v{module_instance.get_version()}")
                        return True
                    else:
                        print(f"[-] Module {module_name} init failed")
                        return False
            
            return False
            
        except Exception as e:
            print(f"[-] Error loading module {module_name}: {e}")
            traceback.print_exc()
            return False
    
    def unload_module(self, module_name: str) -> bool:
        """Unload a module"""
        if module_name not in self.modules:
            return False
        
        try:
            # Stop thread if running
            self.stop_module_thread(module_name)
            
            # Cleanup
            module = self.modules[module_name]
            module.cleanup()
            module.on_unload()
            
            # Remove from dict
            del self.modules[module_name]
            del self.module_states[module_name]
            
            print(f"[+] Unloaded module: {module_name}")
            return True
            
        except Exception as e:
            print(f"[-] Error unloading module {module_name}: {e}")
            return False
    
    def reload_module(self, module_name: str) -> bool:
        """Reload a module"""
        if module_name not in self.modules:
            return False
        
        # Unload
        if not self.unload_module(module_name):
            return False
        
        # Reload
        return self.load_module(module_name)
    
    def get_module(self, name: str) -> Optional[Module]:
        """Get module by name"""
        return self.modules.get(name)
    
    def get_all_modules(self) -> Dict[str, Module]:
        """Get all loaded modules"""
        return self.modules.copy()
    
    def get_module_info(self, name: str) -> Optional[Dict]:
        """Get module information"""
        if name in self.module_states:
            return self.module_states[name].copy()
        return None
    
    def get_all_module_info(self) -> Dict:
        """Get all module information"""
        return self.module_states.copy()
    
    def execute_module(self, name: str, args: Dict = None) -> Dict:
        """Execute a module"""
        args = args or {}
        
        if name not in self.modules:
            return {
                'success': False,
                'error': f"Module {name} not found",
                'module': name
            }
        
        try:
            result = self.modules[name].execute(args)
            if isinstance(result, dict):
                result['module'] = name
                return result
            else:
                return {
                    'success': True,
                    'result': result,
                    'module': name
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'module': name
            }
    
    def start_module_thread(self, name: str, args: Dict = None, 
                           interval: int = 60) -> bool:
        """Start a module in its own thread (continuous execution)"""
        if name not in self.modules or name in self.module_threads:
            return False
        
        def run_module():
            while self.running:
                try:
                    result = self.execute_module(name, args or {})
                    if not result.get('success', False):
                        time.sleep(interval)
                    time.sleep(1)
                except Exception as e:
                    print(f"[!] Module {name} thread error: {e}")
                    time.sleep(interval)
        
        thread = threading.Thread(target=run_module, daemon=True, name=f"Module-{name}")
        self.module_threads[name] = thread
        thread.start()
        return True
    
    def stop_module_thread(self, name: str) -> bool:
        """Stop a module thread"""
        if name in self.module_threads:
            try:
                # Signal to stop
                self.module_threads[name].join(timeout=5)
                del self.module_threads[name]
                return True
            except:
                pass
        return False
    
    def register_event_handler(self, event_name: str, handler: Callable):
        """Register an event handler"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    def trigger_event(self, event_name: str, data: Dict = None):
        """Trigger an event"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    handler(data or {})
                except Exception as e:
                    print(f"[!] Event handler error: {e}")
    
    def cleanup_all(self):
        """Cleanup all modules"""
        self.running = False
        
        # Stop all threads
        for name in list(self.module_threads.keys()):
            self.stop_module_thread(name)
        
        # Cleanup modules
        for name in list(self.modules.keys()):
            try:
                self.modules[name].cleanup()
            except:
                pass
        
        self.modules.clear()
        self.module_states.clear()
        self.event_handlers.clear()


# ============================================================================
# EXAMPLE PLUGIN TEMPLATE
# ============================================================================

class ExamplePlugin(Module):
    """Example plugin template"""
    
    def get_name(self) -> str:
        return "example_plugin"
    
    def get_description(self) -> str:
        return "Example plugin for demonstration"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_dependencies(self) -> List[str]:
        return []
    
    def init(self) -> bool:
        print("[*] Example plugin initialized")
        return True
    
    def cleanup(self) -> bool:
        print("[*] Example plugin cleaned up")
        return True
    
    def on_load(self):
        print("[*] Example plugin loaded")
    
    def on_unload(self):
        print("[*] Example plugin unloaded")
    
    def get_commands(self) -> Dict[str, Callable]:
        return {
            'example_cmd': self.example_command
        }
    
    def example_command(self, args: Dict) -> Dict:
        return {'output': 'Example command executed'}
    
    def execute(self, args: Dict) -> Dict:
        print(f"[*] Example plugin executing with args: {args}")
        
        return {
            'success': True,
            'message': 'Example plugin executed',
            'args': args,
            'timestamp': time.time()
        }
