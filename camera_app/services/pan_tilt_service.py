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
import cv2

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
        self.pan_angle = 120  # 0-180, default is center
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
        
        # Enhanced IBVS parameters from MATLAB implementation
        self.f = 0.02      # focal length in meters (approximate)
        self.s_x = 4.8e-6  # pixel size in x (meters/pixel)
        self.s_y = 4.8e-6  # pixel size in y (meters/pixel)
        
        # Assumed depth - will be updated based on target size
        self.target_depth = 1.0  # Initial depth estimate (meters)
        
        # Error history for convergence analysis
        self.error_history = []
        self.max_error_history = 30  # Keep last 30 error values
        
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
    
    def calculate_control(self, target_x, target_y, target_width=None, target_height=None):
        """
        Calculate pan and tilt adjustments using IBVS with enhanced interaction matrix.
        
        Args:
            target_x: x-coordinate of the target in the image
            target_y: y-coordinate of the target in the image
            target_width: width of the target (for depth estimation)
            target_height: height of the target (for depth estimation)
            
        Returns:
            Tuple of (pan_adjustment, tilt_adjustment)
        """
        # Calculate normalized image coordinates (relative to center)
        # The origin is at the center of the image
        x = (target_x - self.center_x) * self.s_x
        y = (target_y - self.center_y) * self.s_y
        
        # Calculate error (distance from center in normalized coordinates)
        e_x = x
        e_y = y
        
        # Calculate error (distance from center in pixel coordinates)
        error_x = target_x - self.center_x
        error_y = target_y - self.center_y
        
        # Calculate error magnitude for history
        error_magnitude = np.sqrt(error_x**2 + error_y**2)
        self.error_history.append(error_magnitude)
        
        # Keep error history at specified size
        if len(self.error_history) > self.max_error_history:
            self.error_history.pop(0)
        
        # Apply deadzone to prevent jitter when close to center
        if abs(error_x) < self.deadzone:
            error_x = 0
            e_x = 0
        if abs(error_y) < self.deadzone:
            error_y = 0
            e_y = 0
            
        # Estimate depth if width and height are provided
        if target_width is not None and target_height is not None:
            # Simple depth estimation based on target size
            # Assuming larger objects are closer
            # This is a simplified model - in real applications, you'd use a proper
            # depth model based on known target dimensions
            target_size = target_width * target_height
            # Adjust depth based on target size (inverse relationship)
            if target_size > 0:
                # Normalize by maximum possible size (full frame)
                normalized_size = target_size / (self.center_x * 2 * self.center_y * 2)
                # Depth ranges from 0.5 to 3.0 meters based on size
                self.target_depth = 0.5 + (1.0 - min(normalized_size, 1.0)) * 2.5
        
        # Construct the interaction matrix (Image Jacobian)
        # This matrix relates changes in image features to camera velocity
        L = np.array([
            [-self.f / self.target_depth, 0, e_x / self.target_depth],
            [0, -self.f / self.target_depth, e_y / self.target_depth]
        ])
        
        # Define the error vector
        e = np.array([e_x, e_y])
        
        # IBVS control law: v = -lambda * L+ * e
        # Where L+ is the pseudo-inverse of L, and lambda is the gain
        try:
            # Use Moore-Penrose pseudo-inverse to handle non-square matrices
            L_pinv = np.linalg.pinv(L)
            # Calculate control velocity
            v = -self.gain * L_pinv.dot(e)
            
            # Extract pan and tilt velocity components
            # v[0] is x component (corresponds to tilt)
            # v[1] is y component (corresponds to pan)
            # v[2] is z component (depth, not used directly)
            
            # Scale to appropriate control signals for the servos
            pan_adjustment = v[1] * 25.0  # Vertical axis (pan)
            tilt_adjustment = v[0] * 20.0  # Horizontal axis (tilt)
            
            # Apply smoothing factor
            pan_adjustment *= self.smoothing
            tilt_adjustment *= self.smoothing
        except np.linalg.LinAlgError:
            # Fallback to simplified control if matrix inversion fails
            self.logger.warning("Matrix inversion failed in IBVS control, using fallback")
            
            # CORRECTED AXIS ASSIGNMENT BASED ON OBSERVATIONS:
            pan_adjustment = -error_y * self.gain / self.center_y * 25
            tilt_adjustment = error_x * self.gain / self.center_x * 20
            
            # Apply smoothing
            pan_adjustment *= self.smoothing
            tilt_adjustment *= self.smoothing
        
        # Check if error is converging
        if len(self.error_history) >= 5:
            recent_errors = self.error_history[-5:]
            if max(recent_errors) - min(recent_errors) < 2.0 and np.mean(recent_errors) < 10.0:
                # If error is small and stable, reduce adjustments to avoid oscillation
                pan_adjustment *= 0.5
                tilt_adjustment *= 0.5
                
        return (pan_adjustment, tilt_adjustment)
    
    def update_tracking_target(self, target_id=None):
        """Set the ID of the target to track."""
        with self.tracking_lock:
            self.target_id = target_id
            if self.target_id is not None:
                self.logger.info(f"Updated tracking target to balloon ID: {target_id}")
    
    def reset_tracking(self):
        """Reset tracking parameters and clear error history."""
        self.error_history = []
        self.target_depth = 1.0
        
        # Reset target position to current position
        self.target_pan = self.pan_angle
        self.target_tilt = self.tilt_angle
        
        # Log the reset
        self.logger.info("Tracking parameters reset")
    
    def get_error_stats(self):
        """Get statistics about the tracking error for monitoring."""
        if not self.error_history:
            return None
            
        stats = {
            "current_error": self.error_history[-1] if self.error_history else 0,
            "avg_error": np.mean(self.error_history) if self.error_history else 0,
            "min_error": min(self.error_history) if self.error_history else 0,
            "max_error": max(self.error_history) if self.error_history else 0,
            "is_converged": False
        }
        
        # Check if tracking has converged
        if len(self.error_history) >= 5:
            recent_errors = self.error_history[-5:]
            if max(recent_errors) - min(recent_errors) < 2.0 and np.mean(recent_errors) < 10.0:
                stats["is_converged"] = True
                
        return stats
    
    def start_tracking(self, target_id=None):
        """
        Start tracking a specific balloon ID or any detected balloon.
        
        Args:
            target_id: ID of the balloon to track, or None to track any detected balloon
        """
        if self.is_tracking:
            self.stop_tracking()
        
        # Reset tracking parameters
        self.reset_tracking()
        
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
                
                # Calculate control adjustments for pan and tilt using width and height for depth estimation
                pan_adj, tilt_adj = self.calculate_control(target_x, target_y, w, h)
                
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
    
    def draw_tracking_visualization(self, frame, target_detection=None):
        """
        Draw IBVS tracking visualization on the frame.
        
        Args:
            frame: The camera frame to draw on
            target_detection: The target detection [x, y, w, h, ...] if available
            
        Returns:
            Modified frame with visualization
        """
        if frame is None:
            return None
            
        # Get frame dimensions
        height, width = frame.shape[:2]
        
        # Draw frame center
        cv2.drawMarker(frame, (self.center_x, self.center_y), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
        
        # Draw deadzone
        cv2.circle(frame, (self.center_x, self.center_y), self.deadzone, (0, 255, 0), 1)
        
        # If tracking is active, draw more details
        if self.is_tracking and target_detection is not None:
            # Extract target position
            x, y, w, h = target_detection[:4]
            target_x = x + w//2
            target_y = y + h//2
            
            # Draw target center
            cv2.drawMarker(frame, (target_x, target_y), (0, 0, 255), cv2.MARKER_CROSS, 15, 2)
            
            # Draw line from center to target
            cv2.line(frame, (self.center_x, self.center_y), (target_x, target_y), (255, 0, 0), 2)
            
            # Draw error vector
            error_x = target_x - self.center_x
            error_y = target_y - self.center_y
            error_magnitude = np.sqrt(error_x**2 + error_y**2)
            
            # Get error stats
            stats = self.get_error_stats()
            
            # Draw text with error information
            error_text = f"Error: {error_magnitude:.1f}px"
            cv2.putText(frame, error_text, (width - 300, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Draw convergence status
            if stats and stats.get("is_converged", False):
                cv2.putText(frame, "Converged", (width - 300, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Draw camera parameters
            depth_text = f"Est. Depth: {self.target_depth:.2f}m"
            cv2.putText(frame, depth_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Draw servo angles
            angles_text = f"Pan: {self.pan_angle:.1f}° Tilt: {self.tilt_angle:.1f}°"
            cv2.putText(frame, angles_text, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame 