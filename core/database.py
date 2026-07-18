#!/usr/bin/env python3
"""
Database Handler
"""

import sqlite3
import os
import time
from typing import List
from dataclasses import dataclass

# Import from parent
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from c2_server import Beacon, Command, Protocol, BeaconStatus, CommandStatus

class C2Database:
    def __init__(self, db_path: str = "data/c2_framework.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS beacons (
                beacon_id TEXT PRIMARY KEY,
                hostname TEXT,
                username TEXT,
                os_type TEXT,
                os_version TEXT,
                architecture TEXT,
                ip_address TEXT,
                pid INTEGER,
                protocol TEXT,
                last_beacon REAL,
                status TEXT,
                integrity_level TEXT,
                is_admin INTEGER,
                created_at REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                command_id TEXT PRIMARY KEY,
                beacon_id TEXT,
                command_type TEXT,
                command_args TEXT,
                status TEXT,
                timestamp REAL,
                executed_at REAL,
                output TEXT,
                error_msg TEXT
            )
        """)
        
        cursor.execute("""CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            level TEXT,
            message TEXT
        )""")
        
        conn.commit()
        conn.close()
    
    def add_beacon(self, beacon: Beacon):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO beacons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            beacon.beacon_id, beacon.hostname, beacon.username, beacon.os_type,
            beacon.os_version, beacon.architecture, beacon.ip_address, beacon.pid,
            beacon.protocol.value, beacon.last_beacon, beacon.status.value,
            beacon.integrity_level, int(beacon.is_admin), beacon.created_at
        ))
        conn.commit()
        conn.close()
    
    def get_beacons(self) -> List[Beacon]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM beacons")
        beacons = []
        for row in cursor.fetchall():
            beacon = Beacon(
                beacon_id=row[0], hostname=row[1], username=row[2],
                os_type=row[3], os_version=row[4], architecture=row[5],
                ip_address=row[6], pid=row[7],
                protocol=Protocol(row[8]), last_beacon=row[9],
                status=BeaconStatus(row[10]), integrity_level=row[11],
                is_admin=bool(row[12]), created_at=row[13]
            )
            beacons.append(beacon)
        conn.close()
        return beacons
    
    def log_message(self, level: str, message: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)",
                      (time.time(), level, message))
        conn.commit()
        conn.close()
