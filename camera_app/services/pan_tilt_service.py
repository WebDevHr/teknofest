#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pan-Tilt Control Service
----------------------
Service for controlling pan-tilt mechanism using Image-Based Visual Servoing (IBVS).
Uses a 2-DOF pan-tilt platform connected to an Arduino on COM7.
"""

import serial
import time
import threading
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService

class PanTiltService(QObject):
    """
    Service for tracking objects using a pan-tilt mechanism controlled via Arduino.
    Implements Image-Based Visual Servoing (IBVS) for smooth tracking.
    
    Pin and axis assignments based on physical setup:
    - Pan servo on A1 (controls vertical movement)
    - Tilt servo on A0 (controls horizontal movement)
    
    Movement directions:
    - Pan: When object is below center, servo moves down
    - Pan: When object is above center, servo moves up
    - Tilt: When object is right of center, servo moves right
    - Tilt: When object is left of center, servo moves left
    """
    
    # Signals
    command_sent = pyqtSignal(str)  # Signal emitted when a command is sent
    
    def __init__(self, serial_port="COM7", baud_rate=115200):
        super().__init__()
        self.logger = LoggerService()
        
        # Serial connection parameters
        self.serial_port = serial_port
        self.baud_rate = baud_rate
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
        
        # Control parameters
        self.gain = 0.2  # Gain for IBVS control law (higher = faster but may overshoot)
        self.deadzone = 5  # Pixel deadzone in center where no movement is needed
        self.smoothing = 0.8  # Smoothing factor (0-1, higher = smoother)
        
        # Minimum adjustment threshold to avoid tiny movements
        self.min_adjustment = 0.2  # Minimum angle change to actually move servos
        
        # Exponential moving average for servo positions
        self.ema_factor = 0.8  # EMA factor for position filtering (higher = faster response)
        self.target_pan = self.pan_angle
        self.target_tilt = self.tilt_angle
        
        # Frame center coordinates (will be updated based on actual frame size)
        self.center_x = 640 // 2
        self.center_y = 480 // 2
        
        # Tracking parameters
        self.target_id = None  # ID of balloon to track, None means track any detected balloon
        self.is_tracking = False
        self.tracking_thread = None
        self.tracking_lock = threading.Lock()
        
        # Initialize
        self.logger.info("Pan-Tilt Service initialized")
    
    def set_frame_center(self, width, height):
        """Set the center point of the frame."""
        self.center_x = width // 2
        self.center_y = height // 2
        self.logger.info(f"Frame center updated to ({self.center_x}, {self.center_y})")
    
    def connect(self):
        """Connect to the Arduino."""
        if self.is_connected:
            self.logger.info("Already connected to Arduino")
            return True
            
        try:
            # Try to connect to Arduino
            self.serial_conn = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            
            # Give Arduino time to initialize
            time.sleep(2)
            
            # Send initial position to center the servos
            self.move_to(90, 90)
            
            self.is_connected = True
            self.logger.info(f"Connected to Arduino on {self.serial_port}")
            return True
            
        except Exception as e:
            self.is_connected = False
            self.logger.error(f"Failed to connect to Arduino: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from Arduino."""
        # Stop tracking if active
        if self.is_tracking:
            self.stop_tracking()
            
        try:
            if self.serial_conn:
                # Center servos before disconnecting
                self.move_to(90, 90)
                
                # Close the connection
                self.serial_conn.close()
                self.serial_conn = None
                self.is_connected = False
                self.logger.info("Disconnected from Arduino")
                return True
        except Exception as e:
            self.logger.error(f"Error disconnecting from Arduino: {str(e)}")
            return False
    
    def send_command(self, command_str):
        """Send a command to the Arduino."""
        if not self.is_connected or not self.serial_conn:
            self.logger.warning("Cannot send command: Not connected to Arduino")
            return False
            
        try:
            # Ensure command ends with newline
            if not command_str.endswith('\n'):
                command_str += '\n'
            
            # Send command
            self.serial_conn.write(command_str.encode())
            
            # Emit signal
            self.command_sent.emit(command_str)
            
            self.logger.info(f"Sent command: {command_str.strip()}")
            
            # Wait for command to be processed
            time.sleep(0.05)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending command to Arduino: {str(e)}")
            return False
    
    def move_to(self, pan, tilt):
        """Move servos to specific angles."""
        # Constrain angles to limits
        pan = max(self.pan_min, min(self.pan_max, pan))
        tilt = max(self.tilt_min, min(self.tilt_max, tilt))
        
        # Limit maximum movement per step to reduce jerkiness
        max_step = 2.0  # Maximum degrees to move in a single step
        
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
        
        # Round to nearest integer to avoid tiny movements
        pan = round(pan)
        tilt = round(tilt)
        
        # Skip if no actual change
        if pan == self.pan_angle and tilt == self.tilt_angle:
            return True
            
        # Update current angles
        self.pan_angle = pan
        self.tilt_angle = tilt
        
        # Send command to Arduino: format "P{pan}T{tilt}"
        command = f"P{int(pan)}T{int(tilt)}"
        return self.send_command(command)
    
    def move_by(self, pan_delta, tilt_delta):
        """Move servos by relative amounts."""
        # Ignore very small adjustments to avoid jitter
        if abs(pan_delta) < self.min_adjustment:
            pan_delta = 0
        if abs(tilt_delta) < self.min_adjustment:
            tilt_delta = 0
            
        # Update target position with EMA filtering
        self.target_pan = self.target_pan + pan_delta
        self.target_tilt = self.target_tilt + tilt_delta
        
        # Apply EMA filter to current position for smooth movement
        new_pan = self.pan_angle * (1 - self.ema_factor) + self.target_pan * self.ema_factor
        new_tilt = self.tilt_angle * (1 - self.ema_factor) + self.target_tilt * self.ema_factor
        
        # Move to new position
        return self.move_to(new_pan, new_tilt)
    
    def calculate_control(self, target_x, target_y):
        """
        Calculate pan and tilt adjustments using IBVS.
        
        Args:
            target_x: x-coordinate of the target in the image
            target_y: y-coordinate of the target in the image
            
        Returns:
            Tuple of (pan_adjustment, tilt_adjustment)
        """
        # Calculate error (distance from center)
        error_x = target_x - self.center_x
        error_y = target_y - self.center_y
        
        # Apply deadzone to prevent jitter when close to center
        if abs(error_x) < self.deadzone:
            error_x = 0
        if abs(error_y) < self.deadzone:
            error_y = 0
            
        # CORRECTED AXIS ASSIGNMENT BASED ON OBSERVATIONS:
        
        # Pan (A1) should respond to vertical error (error_y)
        # When target is above (negative error_y), pan should move up
        # When target is below (positive error_y), pan should move down
        pan_adjustment = -error_y * self.gain / self.center_y * 25
        
        # Tilt (A0) should respond to horizontal error (error_x)
        # When target is to the right (positive error_x), tilt should move right
        # When target is to the left (negative error_x), tilt should move left
        tilt_adjustment = error_x * self.gain / self.center_x * 20
        
        # Apply smoothing (lower adjustment = smoother movement)
        pan_adjustment *= self.smoothing
        tilt_adjustment *= self.smoothing
        
        return (pan_adjustment, tilt_adjustment)
    
    def update_tracking_target(self, target_id=None):
        """Set the ID of the target to track."""
        with self.tracking_lock:
            self.target_id = target_id
            if self.target_id is not None:
                self.logger.info(f"Updated tracking target to balloon ID: {target_id}")
    
    def start_tracking(self, target_id=None):
        """
        Start tracking a specific balloon ID or any detected balloon.
        
        Args:
            target_id: ID of the balloon to track, or None to track any detected balloon
        """
        if self.is_tracking:
            self.stop_tracking()
        
        # Set target ID
        self.update_tracking_target(target_id)
        
        # Start tracking thread
        self.is_tracking = True
        self.tracking_thread = threading.Thread(target=self._tracking_loop)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
        self.logger.info(f"Started tracking {'balloon ID: ' + str(target_id) if target_id is not None else 'any detected balloon'}")
    
    def stop_tracking(self):
        """Stop the tracking."""
        if not self.is_tracking:
            return
            
        # Stop tracking thread
        self.is_tracking = False
        if self.tracking_thread:
            self.tracking_thread.join(timeout=1.0)
            self.tracking_thread = None
        
        self.logger.info("Stopped tracking")
    
    def _tracking_loop(self):
        """Background thread for tracking."""
        self.logger.info("Tracking loop started")
        
        while self.is_tracking:
            try:
                # Sleep for shorter interval to increase responsiveness
                time.sleep(0.01)  # 10ms interval for faster response
                
                # Skip if no detection service available
                if not hasattr(self, 'balloon_detections') or not self.balloon_detections:
                    continue
                
                # Find the target based on ID or select the best one
                target_detection = self._find_target_detection()
                if not target_detection:
                    continue
                
                # Extract target position (center of bounding box)
                x, y, w, h = target_detection[:4]
                target_x = x + w//2
                target_y = y + h//2
                
                # Calculate control adjustments for pan and tilt
                pan_adj, tilt_adj = self.calculate_control(target_x, target_y)
                
                # Apply the adjustments
                self.move_by(pan_adj, tilt_adj)
                
            except Exception as e:
                self.logger.error(f"Error in tracking loop: {str(e)}")
        
        self.logger.info("Tracking loop ended")
    
    def _find_target_detection(self):
        """Find the target detection based on target_id or select the most confident one."""
        with self.tracking_lock:
            # Return None if no detections
            if not self.balloon_detections:
                return None
                
            # If tracking a specific ID
            if self.target_id is not None:
                for detection in self.balloon_detections:
                    if len(detection) > 6 and detection[6] == self.target_id:
                        return detection
                        
                # Target ID not found in current detections
                return None
            
            # If not tracking a specific ID, pick the largest balloon
            # (which is likely closest to the camera)
            largest_detection = None
            largest_area = 0
            
            for detection in self.balloon_detections:
                x, y, w, h = detection[:4]
                area = w * h
                
                if area > largest_area:
                    largest_area = area
                    largest_detection = detection
                    
                    # If we found a detection with a track ID, update our target ID
                    if len(detection) > 6 and detection[6] != -1:
                        self.target_id = detection[6]
                        self.logger.info(f"Auto-selected tracking target: balloon ID {self.target_id}")
            
            return largest_detection
    
    def set_detections(self, detections):
        """Set the current balloon detections."""
        with self.tracking_lock:
            self.balloon_detections = detections
    
    def release(self):
        """Release resources."""
        self.stop_tracking()
        self.disconnect()
        self.logger.info("Pan-Tilt Service resources released")
        
    def set_balloon_detector(self, balloon_detector):
        """Connect to the balloon detector service."""
        # Connect the balloon detector signal to our slot
        balloon_detector.detection_ready.connect(self._on_detection_ready)
    
    def _on_detection_ready(self, frame, detections):
        """Slot for handling new detections from the balloon detector."""
        # Update detections
        self.set_detections(detections) 