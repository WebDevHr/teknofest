#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pan-Tilt Service
----------------------
Service for controlling pan-tilt mechanism using Image-Based Visual Servoing (IBVS).
Uses a 2-DOF pan-tilt platform connected to a ServoControlService.
"""

import time
import threading
import math
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService
from services.servo_control_service import ServoControlService
from utils.config import config

class PanTiltService(QObject):
    """
    Service for implementing Image-Based Visual Servoing (IBVS) for pan-tilt control.
    
    This service handles the IBVS algorithm for tracking and sends movement commands
    to the ServoControlService which handles the actual Arduino communication.
    """
    
    # Signals
    tracking_update = pyqtSignal(int, int, int, int)  # target_x, target_y, pan, tilt
    connection_status_changed = pyqtSignal(bool)  # Signal for connection status changes, forwarded from ServoControlService
    
    def __init__(self):
        super().__init__()
        self.logger = LoggerService()
        
        # Get the singleton ServoControlService instance
        self.servo_service = ServoControlService.get_instance()
        
        # Connect to the connection status signal of the servo service
        self.servo_service.connection_status_changed.connect(self._on_connection_status_changed)
        
        # Current servo positions (degrees) - get from servo service
        self.pan_angle, self.tilt_angle = self.servo_service.get_current_angles()
        
        # Reference to servo limits - these are just references to the actual limits in ServoControlService
        self.pan_min = self.servo_service.pan_min
        self.pan_max = self.servo_service.pan_max
        self.tilt_min = self.servo_service.tilt_min
        self.tilt_max = self.servo_service.tilt_max
        
        # Control parameters
        self.gain = 0.5  # Gain for IBVS control law
        self.deadzone = 5  # Pixel deadzone in center where no movement is needed
        self.smoothing = 0.7  # Smoothing factor (0-1, higher = smoother)
        
        # Exponential moving average for servo positions
        self.ema_factor = 0.7  # EMA factor for position filtering (higher = faster response)
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
        
        # Store the last detections from the detector service
        self.last_detections = []
        self.current_image_point = None
        
        # Initialize
        self.logger.info("IBVS Pan-Tilt Service initialized")
    
    def set_frame_center(self, width, height):
        """Set the center point of the frame."""
        self.center_x = width // 2
        self.center_y = height // 2
        self.logger.info(f"Frame center updated to ({self.center_x}, {self.center_y})")
    
    def connect(self):
        """Connect to the Arduino via ServoControlService."""
        # Just forward to the servo service
        return self.servo_service.connect()
    
    @property
    def is_connected(self):
        """Check if connected to Arduino via the servo service."""
        return self.servo_service.is_connected
    
    def disconnect(self):
        """Disconnect from Arduino via ServoControlService."""
        # Stop tracking if active
        if self.is_tracking:
            self.stop_tracking()
            
        # We don't actually disconnect since other services might be using it
        # Just log that we're no longer using it
        self.logger.info("IBVS Pan-Tilt Service no longer using servo connection")
        return True
    
    def move_to(self, pan, tilt):
        """Move servos to specific angles via ServoControlService."""
        # Forward to servo service and update our local angle variables
        result = self.servo_service.move_to(pan, tilt)
        
        # Update our local angles to match the servo service's angles
        self.pan_angle, self.tilt_angle = self.servo_service.get_current_angles()
        
        return result
    
    def move_by(self, pan_delta, tilt_delta):
        """Move servos by relative amounts via ServoControlService."""
        # Forward to servo service
        result = self.servo_service.move_by(pan_delta, tilt_delta)
        
        # Update our local angles to match the servo service's angles
        self.pan_angle, self.tilt_angle = self.servo_service.get_current_angles()
        
        return result
    
    def calculate_ibvs_control(self, target_x, target_y):
        """
        Calculate IBVS control law to determine servo movements.
        
        Args:
            target_x: Target x-coordinate in image (pixels)
            target_y: Target y-coordinate in image (pixels)
            
        Returns:
            (pan_delta, tilt_delta): Change in pan/tilt angles to track target
        """
        # Skip if target is close enough to center
        dx = target_x - self.center_x
        dy = target_y - self.center_y
        
        # If target is in deadzone, don't move
        if abs(dx) < self.deadzone and abs(dy) < self.deadzone:
            return (0, 0)
            
        # Calculate error (using negative dx for tilt because higher tilt moves target right)
        tilt_error = -dx
        pan_error = dy
        
        # Apply gain (P controller)
        pan_delta = self.gain * pan_error / 100.0  # Normalize for reasonable delta
        tilt_delta = self.gain * tilt_error / 100.0  # Normalize for reasonable delta
        
        # Apply smoothing
        pan_delta = self.smoothing * pan_delta
        tilt_delta = self.smoothing * tilt_delta
        
        return (pan_delta, tilt_delta)
    
    def update_tracking_target(self, target_id=None):
        """Update the ID of the balloon to track."""
        self.target_id = target_id
        self.logger.info(f"Tracking target updated: {target_id}")
    
    def start_tracking(self, target_id=None):
        """Start tracking balloon with given ID (or any balloon if None)."""
        if self.is_tracking:
            self.logger.info("Tracking already active")
            return
            
        # Set tracking target
        self.target_id = target_id
        
        # Set tracking flag
        self.is_tracking = True
        
        # Start tracking thread
        self.tracking_thread = threading.Thread(target=self._tracking_loop)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
        self.logger.info(f"IBVS Tracking started for target ID: {target_id if target_id is not None else 'any'}")
    
    def stop_tracking(self):
        """Stop tracking."""
        if not self.is_tracking:
            return
            
        # Clear tracking flag to stop thread
        self.is_tracking = False
        
        # Wait for thread to finish
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=0.5)
            
        self.logger.info("IBVS Tracking stopped")
    
    def _tracking_loop(self):
        """Background thread for continuous tracking."""
        self.logger.info("IBVS Tracking loop started")
        
        # Initialize tick rate limiting
        last_tick = time.time()
        loop_delay = 0.02  # 50Hz max
        
        while self.is_tracking:
            now = time.time()
            elapsed = now - last_tick
            
            # Limit update rate
            if elapsed < loop_delay:
                time.sleep(loop_delay - elapsed)
                continue
                
            # Update last tick time
            last_tick = time.time()
            
            # Find balloon to track
            detection = self._find_target_detection()
            
            # Skip if no balloon found
            if not detection:
                time.sleep(0.05)  # Short sleep to avoid busy-waiting
                continue
                
            # Extract target coordinates and ID
            x, y, w, h, confidence, class_id, track_id = detection
            cx = int(x + w / 2)
            cy = int(y + h / 2)
            
            # Store current point for visualization
            self.current_image_point = (cx, cy)
            
            # Calculate control
            with self.tracking_lock:
                pan_delta, tilt_delta = self.calculate_ibvs_control(cx, cy)
                
                # Apply control using the servo service
                self.move_by(pan_delta, tilt_delta)
                
                # Emit tracking update signal with our local angle values
                self.tracking_update.emit(cx, cy, int(self.pan_angle), int(self.tilt_angle))
    
    def _find_target_detection(self):
        """Find appropriate balloon detection to track."""
        # No balloon detector attached
        if not hasattr(self, 'balloon_detector') or not self.balloon_detector:
            return None
            
        # Get the latest detections
        detections = self.balloon_detector.last_frame_detections
        
        # No detections available
        if not detections:
            return None
            
        if self.target_id is not None:
            # Look for specific balloon ID
            for detection in detections:
                if len(detection) > 6 and detection[6] == self.target_id:
                    return detection
        else:
            # Track the largest balloon
            best_detection = None
            max_area = 0
            
            for detection in detections:
                if len(detection) >= 4:
                    _, _, w, h = detection[:4]
                    area = w * h
                    if area > max_area:
                        max_area = area
                        best_detection = detection
                        
            return best_detection
        
        return None
    
    def set_balloon_detector(self, balloon_detector):
        """Set balloon detector to get detections from."""
        self.balloon_detector = balloon_detector
        self.logger.info("Balloon detector connected to IBVS service")
    
    def release(self):
        """Release resources."""
        self.stop_tracking()
        # Don't disconnect since other services might be using the servo service
        self.logger.info("IBVS Pan-Tilt Service resources released")
    
    def _on_connection_status_changed(self, connected):
        """Handle connection status changes from the servo service."""
        # Just forward the signal
        self.connection_status_changed.emit(connected) 
        
    def draw_tracking_visualization(self, frame, target_detection=None):
        """Draw tracking visualization on frame."""
        import cv2
        
        if not self.is_tracking or frame is None:
            return frame
            
        # Copy frame to avoid modifying original
        vis_frame = frame.copy()
        
        # Draw center crosshair
        cv2.drawMarker(vis_frame, (self.center_x, self.center_y), 
                      (0, 255, 0), markerType=cv2.MARKER_CROSS, 
                      markerSize=20, thickness=2)
        
        # Draw center circle (deadzone)
        cv2.circle(vis_frame, (self.center_x, self.center_y), 
                  self.deadzone, (0, 255, 0), 1)
        
        # If we have a current detection to track
        if target_detection is not None:
            # Extract target coordinates and ID
            x, y, w, h, confidence, class_id, track_id = target_detection
            cx = int(x + w / 2)
            cy = int(y + h / 2)
            
            # Store the current image point
            self.current_image_point = (cx, cy)
            
            # Draw line from center to target
            cv2.line(vis_frame, (self.center_x, self.center_y), (cx, cy), (0, 0, 255), 2)
            
            # Draw angle indicators for pan and tilt
            info_text = f"Pan: {self.pan_angle:.1f}°, Tilt: {self.tilt_angle:.1f}°"
            cv2.putText(vis_frame, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Calculate error (distance from center)
            dx = cx - self.center_x
            dy = cy - self.center_y
            error = math.sqrt(dx*dx + dy*dy)
            cv2.putText(vis_frame, f"Error: {error:.1f}px", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            
            # Highlight current target
            cv2.rectangle(vis_frame, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 255), 2)
            
            # Draw target ID if available
            if track_id is not None:
                cv2.putText(vis_frame, f"ID: {track_id}", (int(x), int(y - 10)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        # If we have a stored image point but no current detection
        elif self.current_image_point is not None:
            cx, cy = self.current_image_point
            # Draw the last known position with a different color
            cv2.drawMarker(vis_frame, (int(cx), int(cy)), 
                         (255, 165, 0), markerType=cv2.MARKER_CROSS, 
                         markerSize=15, thickness=1)
        
        # Display tracking mode
        cv2.putText(vis_frame, "IBVS Tracking", (10, self.center_y * 2 - 20),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)
        
        return vis_frame 