#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pan-Tilt Service with IBVS
-------------------------
Service for controlling a 2-DOF pan-tilt mechanism using Image-Based Visual Servoing (IBVS)
to keep tracked balloons centered in the camera frame.
"""

import serial
import time
import numpy as np
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex
from services.logger_service import LoggerService

class PanTiltService(QObject):
    """
    Service for controlling a 2-DOF pan-tilt mechanism using IBVS.
    
    This service takes balloon detections (potentially processed by a Kalman filter) and
    controls pan and tilt servos to keep the target balloon centered in the camera view.
    """
    
    # Signals
    command_sent = pyqtSignal(dict)  # Signal emitted after sending a command
    connection_status_changed = pyqtSignal(bool)  # True if connected, False if disconnected
    
    def __init__(self, serial_port="COM7", baud_rate=115200):
        super().__init__()
        self.logger = LoggerService()
        
        # Serial communication settings
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.serial_connection = None
        self.is_connected = False
        self.connection_lock = QMutex()  # Mutex for thread-safe access to connection
        
        # IBVS parameters
        self.center_x = 320  # Default frame center X (will be updated with actual frame dimensions)
        self.center_y = 240  # Default frame center Y (will be updated with actual frame dimensions)
        
        # Control gains (IBVS parameters)
        self.gain_x = 0.5  # Gain for pan (X) error
        self.gain_y = 0.5  # Gain for tilt (Y) error
        
        # Current servo angles (degrees)
        self.current_pan = 90  # Center position for pan (0-180)
        self.current_tilt = 90  # Center position for tilt (0-180)
        
        # Servo limits
        self.pan_min = 0
        self.pan_max = 180
        self.tilt_min = 0
        self.tilt_max = 180
        
        # Movement smoothing
        self.smooth_factor = 0.7  # 0-1, higher value = smoother movement, but more lag
        
        # Target tracking
        self.tracking_enabled = False
        self.target_id = -1  # ID of the balloon to track
        self.tracking_thread = None
        self.stop_tracking_event = threading.Event()
        
        # Last detected target position
        self.last_target_x = None
        self.last_target_y = None
        self.last_detection_time = 0
        self.detection_timeout = 1.0  # seconds before considering target lost
        
        # Initialize with the image dimensions
        self.logger.info("Pan-Tilt Service initialized")
        
    def set_frame_dimensions(self, width, height):
        """Update the center coordinates based on actual frame dimensions."""
        self.center_x = width // 2
        self.center_y = height // 2
        self.logger.info(f"Frame center updated to ({self.center_x}, {self.center_y})")
    
    def connect(self):
        """Connect to the Arduino controller via serial."""
        self.connection_lock.lock()
        try:
            if self.is_connected:
                self.logger.info("Already connected to Arduino")
                return True
                
            try:
                self.serial_connection = serial.Serial(
                    port=self.serial_port,
                    baudrate=self.baud_rate,
                    timeout=1
                )
                # Wait for Arduino to initialize
                time.sleep(2)
                
                self.is_connected = True
                self.connection_status_changed.emit(True)
                self.logger.info(f"Connected to Arduino on {self.serial_port}")
                
                # Center the servos
                self.move_to_center()
                
                return True
            except serial.SerialException as e:
                self.logger.error(f"Failed to connect to Arduino: {str(e)}")
                self.is_connected = False
                self.connection_status_changed.emit(False)
                return False
        finally:
            self.connection_lock.unlock()
    
    def disconnect(self):
        """Disconnect from the Arduino controller."""
        self.connection_lock.lock()
        try:
            if not self.is_connected:
                return True
                
            try:
                # Stop tracking if active
                self.stop_tracking()
                
                # Close the serial connection
                if self.serial_connection:
                    self.serial_connection.close()
                
                self.is_connected = False
                self.connection_status_changed.emit(False)
                self.logger.info("Disconnected from Arduino")
                return True
            except Exception as e:
                self.logger.error(f"Error disconnecting from Arduino: {str(e)}")
                return False
        finally:
            self.connection_lock.unlock()
    
    def send_command(self, command_str):
        """Send a command string to the Arduino."""
        self.connection_lock.lock()
        try:
            if not self.is_connected:
                self.logger.warning("Cannot send command: Not connected to Arduino")
                return False
                
            try:
                # Add a newline to the command
                if not command_str.endswith('\n'):
                    command_str += '\n'
                    
                # Send the command
                self.serial_connection.write(command_str.encode('utf-8'))
                self.serial_connection.flush()
                
                # Log the command
                self.logger.info(f"Sent command: {command_str.strip()}")
                
                # Emit signal
                cmd_parts = command_str.strip().split(',')
                cmd_dict = {}
                for part in cmd_parts:
                    if ':' in part:
                        key, val = part.split(':', 1)
                        cmd_dict[key] = val
                self.command_sent.emit(cmd_dict)
                
                return True
            except Exception as e:
                self.logger.error(f"Error sending command to Arduino: {str(e)}")
                return False
        finally:
            self.connection_lock.unlock()
    
    def set_servo_angles(self, pan, tilt):
        """Set the servo angles directly."""
        # Constrain angles to valid ranges
        pan = max(self.pan_min, min(self.pan_max, pan))
        tilt = max(self.tilt_min, min(self.tilt_max, tilt))
        
        # Apply smoothing if there are current values
        if self.current_pan is not None and self.current_tilt is not None:
            pan = self.current_pan + (1 - self.smooth_factor) * (pan - self.current_pan)
            tilt = self.current_tilt + (1 - self.smooth_factor) * (tilt - self.current_tilt)
        
        # Update current values
        self.current_pan = pan
        self.current_tilt = tilt
        
        # Send command to Arduino
        command = f"P:{int(pan)},T:{int(tilt)}"
        return self.send_command(command)
    
    def move_to_center(self):
        """Move servos to the center position."""
        return self.set_servo_angles(90, 90)
    
    def calculate_ibvs_control(self, target_x, target_y):
        """
        Calculate pan/tilt adjustments using IBVS algorithm.
        
        Args:
            target_x: Target X position in the image
            target_y: Target Y position in the image
            
        Returns:
            Tuple of (pan_angle, tilt_angle) for the servos
        """
        # Calculate error in the image space
        error_x = target_x - self.center_x
        error_y = target_y - self.center_y
        
        # Invert directions as needed:
        # - For pan: positive error_x (target is to the right) means servo should move right (increase angle)
        # - For tilt: positive error_y (target is lower) means servo should move down (increase angle)
        pan_adjustment = -self.gain_x * error_x
        tilt_adjustment = -self.gain_y * error_y
        
        # Calculate new servo angles
        new_pan = self.current_pan + pan_adjustment
        new_tilt = self.current_tilt + tilt_adjustment
        
        return new_pan, new_tilt
    
    def start_tracking(self, target_id=None):
        """
        Start tracking a specific balloon ID, or the first detected balloon if ID is None.
        
        Args:
            target_id: Optional ID of the balloon to track
        """
        if self.tracking_enabled:
            # Already tracking, update the target ID if provided
            if target_id is not None:
                self.target_id = target_id
                self.logger.info(f"Updated tracking target to balloon ID: {target_id}")
            return
            
        # Start tracking
        self.target_id = target_id
        self.tracking_enabled = True
        
        # Reset the stopping event
        self.stop_tracking_event.clear()
        
        # Start the tracking thread
        self.tracking_thread = threading.Thread(target=self._tracking_loop)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
        self.logger.info(f"Started tracking {'balloon ID: ' + str(target_id) if target_id is not None else 'any detected balloon'}")
    
    def stop_tracking(self):
        """Stop tracking balloons."""
        if not self.tracking_enabled:
            return
            
        # Set the flag to stop tracking
        self.tracking_enabled = False
        self.stop_tracking_event.set()
        
        # Wait for the tracking thread to finish
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=1.0)
        
        self.tracking_thread = None
        self.logger.info("Stopped tracking")
    
    def _tracking_loop(self):
        """Background thread for continuous tracking update."""
        self.logger.info("Tracking loop started")
        
        while self.tracking_enabled and not self.stop_tracking_event.is_set():
            try:
                current_time = time.time()
                
                # Check if we have a recent detection
                if (self.last_target_x is not None and self.last_target_y is not None and 
                    current_time - self.last_detection_time < self.detection_timeout):
                    
                    # Calculate servo angles using IBVS
                    new_pan, new_tilt = self.calculate_ibvs_control(
                        self.last_target_x, self.last_target_y
                    )
                    
                    # Move servos to the calculated position
                    self.set_servo_angles(new_pan, new_tilt)
                
                # Small delay to avoid using too much CPU
                time.sleep(0.05)
                
            except Exception as e:
                self.logger.error(f"Error in tracking loop: {str(e)}")
                time.sleep(0.1)  # Add a small delay after an error
        
        self.logger.info("Tracking loop ended")
    
    def update_target_position(self, detections, frame_width, frame_height):
        """
        Update the target position based on detections.
        
        Args:
            detections: List of detections from the balloon detector service
            frame_width: Width of the current frame
            frame_height: Height of the current frame
            
        Returns:
            True if target was found and updated, False otherwise
        """
        # Update frame dimensions if needed
        if self.center_x != frame_width // 2 or self.center_y != frame_height // 2:
            self.set_frame_dimensions(frame_width, frame_height)
        
        if not self.tracking_enabled or not detections:
            return False
            
        # Find the target balloon
        target_detection = None
        
        if self.target_id is not None:
            # Look for a specific balloon ID
            for detection in detections:
                if len(detection) > 6 and detection[6] == self.target_id:
                    target_detection = detection
                    break
        else:
            # Just take the first detection with highest confidence
            target_detection = max(detections, key=lambda d: d[4] if len(d) > 4 else 0)
            
            # Update target_id if we found a detection with an ID
            if target_detection and len(target_detection) > 6 and target_detection[6] != -1:
                self.target_id = target_detection[6]
                self.logger.info(f"Auto-selected tracking target: balloon ID {self.target_id}")
        
        if target_detection is None:
            return False
            
        # Extract balloon position (center of bounding box)
        x, y, w, h = target_detection[:4]
        center_x = x + w // 2
        center_y = y + h // 2
        
        # Update last known position
        self.last_target_x = center_x
        self.last_target_y = center_y
        self.last_detection_time = time.time()
        
        return True
    
    def release(self):
        """Release resources and disconnect."""
        self.stop_tracking()
        self.disconnect()
        self.logger.info("Pan-Tilt Service resources released") 