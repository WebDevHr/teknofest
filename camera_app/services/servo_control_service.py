#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Servo Control Service
--------------------
Service for controlling pan-tilt servos through Arduino.
Provides centralized servo control for all tracking methods.
Uses a singleton pattern to ensure only one instance controls the hardware.
"""

import serial
import time
import threading
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService
from utils.config import config

class ServoControlService(QObject):
    """
    Singleton service for controlling pan-tilt servos through Arduino.
    
    Pin and axis assignments based on physical setup:
    - Pan servo on A0 (controls vertical movement)
    - Tilt servo on A1 (controls horizontal movement)
    
    Movement directions:
    - Up key: Pan increases (camera moves up)
    - Down key: Pan decreases (camera moves down)
    - Left key: Tilt decreases (camera moves left)
    - Right key: Tilt increases (camera moves right)
    
    Angle ranges:
    - Pan: 0 (looking down) to 180 (looking up)
    - Tilt: 0 (looking left) to 180 (looking right)
    """
    
    # Singleton instance
    _instance = None
    
    # Signals
    command_sent = pyqtSignal(str)  # Signal emitted when a command is sent
    connection_status_changed = pyqtSignal(bool)  # Signal emitted when connection status changes
    
    @staticmethod
    def get_instance():
        """Get singleton instance of ServoControlService."""
        if ServoControlService._instance is None:
            ServoControlService._instance = ServoControlService()
        return ServoControlService._instance
    
    def __init__(self):
        # Check if singleton instance already exists
        if ServoControlService._instance is not None:
            raise Exception("ServoControlService is a singleton! Use get_instance() instead.")
        
        super().__init__()
        self.logger = LoggerService()
        
        # Serial connection parameters from config
        self.serial_port = config.pan_tilt_serial_port
        self.baud_rate = config.pan_tilt_baud_rate
        self.serial_conn = None
        self.is_connected = False
        
        # Current servo positions (degrees)
        self.pan_angle = 90  # 0-180, default is center
        self.tilt_angle = 90  # 0-180, default is center
        
        # Servo limits
        self.pan_min = 0
        self.pan_max = 180
        self.tilt_min = 0
        self.tilt_max = 180
        
        # Minimum adjustment threshold to avoid tiny movements
        self.min_adjustment = 0.1  # Minimum angle change to actually move servos
        
        # Access lock to prevent concurrent access to serial port
        self.serial_lock = threading.Lock()
        
        # Set ourselves as the singleton instance
        ServoControlService._instance = self
        
        # Log initialization
        self.logger.info("Servo Control Service initialized")
    
    def set_limits(self, pan_min, pan_max, tilt_min, tilt_max):
        """Set the servo angle limits."""
        self.pan_min = pan_min
        self.pan_max = pan_max
        self.tilt_min = tilt_min
        self.tilt_max = tilt_max
        self.logger.info(f"Servo limits set: Pan [{pan_min}-{pan_max}], Tilt [{tilt_min}-{tilt_max}]")
    
    def connect(self):
        """Connect to the Arduino."""
        with self.serial_lock:
            if self.is_connected:
                self.logger.info("Arduino bağlantısı zaten kurulmuş")
                return True
                
            try:
                # Log connection attempt
                self.logger.info(f"Arduino bağlantısı kuruluyor: {self.serial_port} ({self.baud_rate} baud)...")
                
                # Try to connect to Arduino
                self.serial_conn = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
                
                # Give Arduino time to initialize - more time needed for stable connection
                self.logger.info("Arduino bağlantısı başlatılıyor, lütfen bekleyin...")
                time.sleep(2.5)
                
                # Set connected flag now that we have a valid connection
                self.is_connected = True
                self.logger.info(f"Arduino bağlantısı başarılı: {self.serial_port}")
                
                # Emit connection status signal
                self.connection_status_changed.emit(True)
                
                # Send initial position to center the servos
                center_result = self.move_to(90, 90)
                if not center_result:
                    self.logger.warning("Servolar merkez pozisyona getirilemedi, ancak bağlantı kuruldu")
                
                return True
                
            except serial.SerialException as e:
                self.is_connected = False
                if "could not open port" in str(e):
                    self.logger.error(f"Arduino bağlantısı kurulamadı: {self.serial_port} portu bulunamadı veya kullanılamıyor")
                else:
                    self.logger.error(f"Arduino bağlantısı kurulamadı: {str(e)}")
                
                # Emit connection status signal
                self.connection_status_changed.emit(False)
                return False
            except Exception as e:
                self.is_connected = False
                self.logger.error(f"Arduino bağlantısında beklenmeyen hata: {str(e)}")
                
                # Emit connection status signal
                self.connection_status_changed.emit(False)
                return False
    
    def disconnect(self):
        """Disconnect from Arduino."""
        with self.serial_lock:
            try:
                if self.serial_conn:
                    # Center servos before disconnecting
                    self.move_to(90, 90)
                    
                    # Close the connection
                    self.serial_conn.close()
                    self.serial_conn = None
                    self.is_connected = False
                    self.logger.info("Disconnected from Arduino")
                    
                    # Emit connection status signal
                    self.connection_status_changed.emit(False)
                    return True
            except Exception as e:
                self.logger.error(f"Error disconnecting from Arduino: {str(e)}")
                return False
    
    def send_command(self, command_str):
        """Send a command to the Arduino."""
        with self.serial_lock:
            if not self.is_connected or not self.serial_conn:
                self.logger.warning(f"Komut gönderilemedi: Arduino bağlantısı yok ({command_str})")
                return False
                
            try:
                # Ensure command ends with newline
                if not command_str.endswith('\n'):
                    command_str += '\n'
                
                # Send command
                self.serial_conn.write(command_str.encode())
                
                # Emit signal
                self.command_sent.emit(command_str)
                
                # Wait for command to be processed
                time.sleep(0.002)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Arduino'ya komut gönderilirken hata: {str(e)}")
                return False
    
    def move_to(self, pan, tilt):
        """Move servos to specific angles."""
        # Constrain angles to limits
        pan = max(self.pan_min, min(self.pan_max, pan))
        tilt = max(self.tilt_min, min(self.tilt_max, tilt))
        
        # Limit maximum movement per step to reduce jerkiness
        max_step = 0.1  # Maximum degrees to move in a single step
        
        if abs(pan - self.pan_angle) > max_step:
            # Limit pan movement
            if pan > self.pan_angle:
                pan = self.pan_angle + max_step
            else:
                pan = self.pan_angle - max_step
        
        if abs(tilt - self.tilt_angle) > max_step:
            # Limit tilt movement
            if tilt > self.tilt_angle:
                tilt = self.tilt_angle + max_step
            else:
                tilt = self.tilt_angle - max_step
        
        # Skip if no actual change (with small threshold for floating point comparison)
        if abs(pan - self.pan_angle) < 0.01 and abs(tilt - self.tilt_angle) < 0.01:
            return True
            
        # Update current angles
        self.pan_angle = pan
        self.tilt_angle = tilt
        
        # Send command to Arduino: format "P{pan}T{tilt}" with 1 decimal precision
        command = f"P{pan:.1f}T{tilt:.1f}"
        return self.send_command(command)
    
    def move_by(self, pan_delta, tilt_delta):
        """Move servos by relative amounts."""
        # Ignore very small adjustments to avoid jitter
        if abs(pan_delta) < self.min_adjustment:
            pan_delta = 0
        if abs(tilt_delta) < self.min_adjustment:
            tilt_delta = 0
            
        # Calculate new angles
        new_pan = self.pan_angle + pan_delta
        new_tilt = self.tilt_angle + tilt_delta
        
        # Move to new position
        return self.move_to(new_pan, new_tilt)
    
    def get_current_angles(self):
        """Get current pan and tilt angles."""
        return (self.pan_angle, self.tilt_angle)
    
    def release(self):
        """Release resources."""
        self.disconnect()
        self.logger.info("Servo Control Service resources released") 