#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PBVS (Position-Based Visual Servoing) Service
----------------------
Service for controlling pan-tilt mechanism using Position-Based Visual Servoing (PBVS).
Uses a 2-DOF pan-tilt platform connected to a ServoControlService.
"""

import time
import threading
import math
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService
from services.servo_control_service import ServoControlService
from utils.config import config
import cv2

class PBVSService(QObject):
    """
    Service for implementing Position-Based Visual Servoing (PBVS) for pan-tilt control.
    
    This service handles the PBVS algorithm for tracking and sends movement commands
    to the ServoControlService which handles the actual Arduino communication.
    """
    
    # Signals
    tracking_update = pyqtSignal(int, int, int, int)  # target_x, target_y, pan, tilt
    connection_status_changed = pyqtSignal(bool)  # Signal for connection status changes, forwarded from ServoControlService
    
    def __init__(self):
        super().__init__()
        self.logger = LoggerService()
        
        # Get the singleton ServoControlService instance
        # Servo bağlantıları:
        # - A0: Pan servo (yatay hareket, soldan sağa, 0-180 derece)
        # - A1: Tilt servo (dikey hareket, aşağıdan yukarıya, 0-180 derece)
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
        self.gain = 0.2  # Gain for PBVS control law
        self.deadzone = 5  # Pixel deadzone in center where no movement is needed
        self.smoothing = 0.8  # Smoothing factor (0-1, higher = smoother)
        
        # Minimum adjustment threshold to avoid tiny movements
        self.min_adjustment = 0.1  # Minimum angle change to actually move servos
        
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
        
        # PBVS specific parameters - camera model
        self.f = 0.02            # focal length (meters)
        self.sx = 800            # pixels per meter
        self.sy = 800            # pixels per meter
        self.cx = self.center_x  # optical center x
        self.cy = self.center_y  # optical center y
        
        # Fixed distance to the scene (Z) - can be updated based on object size
        self.Z = 1.0  # meters (fixed depth assumption)
        
        # Camera offset from pan-tilt center (approximate distance)
        self.camera_offset = 0.1  # 10 cm offset from center of rotation
        
        # Error history for convergence analysis
        self.error_history = []
        self.max_error_history = 30  # Keep last 30 error values
        
        # Current target in image and 3D coordinates
        self.desired_image_point = None  # Desired image coordinates (center of frame)
        self.current_image_point = None  # Current image coordinates of target
        
        # Desired view angles
        self.desired_pan = None
        self.desired_tilt = None
        
        # Store the last detections from the camera service
        self.last_detections = []
        
        # Initialize
        self.logger.info("PBVS Service initialized")
    
    def set_frame_center(self, width, height):
        """Set the center point of the frame."""
        self.center_x = width // 2
        self.center_y = height // 2
        self.cx = self.center_x  # Update optical center
        self.cy = self.center_y  # Update optical center
        self.logger.info(f"Frame center updated to ({self.center_x}, {self.center_y})")
    
    def connect(self):
        """Connect to the Arduino via ServoControlService."""
        # Just forward to the servo service
        return self.servo_service.connect()
    
    def _on_connection_status_changed(self, connected):
        """Handle connection status changes from the servo service."""
        # Forward the signal
        self.connection_status_changed.emit(connected)
    
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
        self.logger.info("PBVS Service no longer using servo connection")
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
        # Ignore very small adjustments to avoid jitter
        if abs(pan_delta) < self.min_adjustment:
            pan_delta = 0
        if abs(tilt_delta) < self.min_adjustment:
            tilt_delta = 0
            
        # Forward to servo service
        result = self.servo_service.move_by(pan_delta, tilt_delta)
        
        # Update our local angles to match the servo service's angles
        self.pan_angle, self.tilt_angle = self.servo_service.get_current_angles()
        
        return result
    
    def calculate_pbvs_control(self, target_x, target_y, target_width=None, target_height=None):
        """
        Calculate PBVS control law to determine servo movements.
        This converts image point to camera coordinates and solves for required angles.
        
        Args:
            target_x: Target x-coordinate in image (pixels)
            target_y: Target y-coordinate in image (pixels)
            target_width: Optional width of target for depth estimation
            target_height: Optional height of target for depth estimation
            
        Returns:
            (pan_delta, tilt_delta): Change in pan/tilt angles to track target
        """
        # Hedefe olan uzaklığı hesapla
        dx = target_x - self.center_x
        dy = target_y - self.center_y
        
        # Update current image point
        self.current_image_point = (target_x, target_y)
        
        # If target is in deadzone, don't move
        if abs(dx) < self.deadzone and abs(dy) < self.deadzone:
            return (0, 0)
        
        # BASIT YAKLAŞIM: Direkt piksel farkını kullanarak servo hareketi hesaplayalım
        # Ters yönlü hareket için negatif işaretler kullanılıyor
        # Normalize etmek için büyük değerlere böl
        pan_delta = -dx / 800.0 * self.gain
        tilt_delta = -dy / 800.0 * self.gain
        
        # Hedef kameranın sağındaysa pan sola gitsin
        # Hedef kameranın solundaysa pan sağa gitsin
        # Hedef kameranın altındaysa tilt yukarı gitsin
        # Hedef kameranın üstündeyse tilt aşağı gitsin
        
        # For debug - keep track of information for visualization
        # Still calculate 3D for visualization
        # Using pinhole camera model: X = Z * (u - cx) / sx
        Xc = self.Z * (target_x - self.cx) / self.sx
        Yc = self.Z * (target_y - self.cy) / self.sy
        Zc = self.Z
        
        # Update depth estimation if size info is available
        if target_width is not None and target_height is not None and target_width > 0 and target_height > 0:
            # Simple depth estimation based on object size
            avg_size = (target_width + target_height) / 2
            estimated_Z = 0.5 * 1000 / avg_size  # Example formula, needs calibration
            
            # Limit to reasonable range and smooth transition
            estimated_Z = max(0.2, min(5.0, estimated_Z))
            self.Z = 0.9 * self.Z + 0.1 * estimated_Z  # Smooth update
        
        # Store desired values for visualization only
        self.desired_pan = -dx / 10.0  # Just for visualization
        self.desired_tilt = -dy / 10.0  # Just for visualization
        
        # Apply smoothing
        pan_delta = self.smoothing * pan_delta
        tilt_delta = self.smoothing * tilt_delta
        
        # Update error history for convergence analysis
        error = math.sqrt(dx**2 + dy**2)  # Euclidean distance error
        self.error_history.append(error)
        
        # Keep history to limited size
        if len(self.error_history) > self.max_error_history:
            self.error_history.pop(0)
            
        return (pan_delta, tilt_delta)
    
    def update_tracking_target(self, target_id=None):
        """Update the ID of the balloon to track."""
        self.target_id = target_id
        self.logger.info(f"Tracking target updated: {target_id}")
    
    def reset_tracking(self):
        """Reset tracking parameters."""
        self.error_history = []
        self.Z = 1.0  # Reset depth assumption
        self.logger.info("Tracking parameters reset")
    
    def get_error_stats(self):
        """Get statistics about tracking error for UI display."""
        if not self.error_history:
            return {
                "current": 0,
                "average": 0,
                "min": 0,
                "max": 0,
                "is_converging": False
            }
            
        current = self.error_history[-1]
        avg = sum(self.error_history) / len(self.error_history)
        min_err = min(self.error_history)
        max_err = max(self.error_history)
        
        # Check if error is converging (last 5 points trend downward)
        is_converging = False
        if len(self.error_history) >= 5:
            recent = self.error_history[-5:]
            is_converging = all(recent[i] >= recent[i+1] for i in range(len(recent)-1))
            
        return {
            "current": round(current, 1),
            "average": round(avg, 1),
            "min": round(min_err, 1),
            "max": round(max_err, 1),
            "is_converging": is_converging
        }
    
    def start_tracking(self, target_id=None):
        """Start tracking balloon with given ID (or any balloon if None)."""
        if self.is_tracking:
            self.logger.info("Tracking already active")
            return
            
        # Set tracking target
        self.target_id = target_id
        
        # Reset tracking parameters
        self.reset_tracking()
        
        # Set tracking flag
        self.is_tracking = True
        
        # Start tracking thread
        self.tracking_thread = threading.Thread(target=self._tracking_loop)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
        self.logger.info(f"PBVS Tracking started for target ID: {target_id if target_id is not None else 'any'}")
    
    def stop_tracking(self):
        """Stop tracking."""
        if not self.is_tracking:
            return
            
        # Clear tracking flag to stop thread
        self.is_tracking = False
        
        # Wait for thread to finish
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=0.5)
            
        self.logger.info("PBVS Tracking stopped")
    
    def _tracking_loop(self):
        """Background thread for continuous tracking."""
        self.logger.info("PBVS Tracking loop started")
        
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
                
            # Extract target coordinates
            cx = int(detection["center_x"])
            cy = int(detection["center_y"])
            width = detection.get("width", None)
            height = detection.get("height", None)
            
            # Calculate control
            with self.tracking_lock:
                pan_delta, tilt_delta = self.calculate_pbvs_control(cx, cy, width, height)
                
                # Apply control
                self.move_by(pan_delta, tilt_delta)
                
                # Emit tracking update signal with our local angle values
                self.tracking_update.emit(cx, cy, int(self.pan_angle), int(self.tilt_angle))
    
    def _find_target_detection(self):
        """Find appropriate balloon detection to track."""
        detections = []
        
        # First check if we have a balloon detector attached
        if hasattr(self, 'balloon_detector') and self.balloon_detector:
            # Get the latest detections - accessing the last_frame_detections property instead of method
            detector_detections = self.balloon_detector.last_frame_detections
            if detector_detections:
                detections.extend(detector_detections)
        
        # Also check if we have detections set directly by the camera service
        if hasattr(self, 'last_detections') and self.last_detections:
            detections.extend(self.last_detections)
        
        # No detections available
        if not detections:
            return None
            
        if self.target_id is not None:
            # Look for specific balloon ID
            for detection in detections:
                if detection.get("id") == self.target_id:
                    return detection
        else:
            # Track the largest balloon
            best_detection = None
            max_area = 0
            
            for detection in detections:
                # Convert detection format to dictionary if it's a list
                if isinstance(detection, list) and len(detection) >= 6:
                    x, y, w, h, conf, class_id = detection[:6]
                    track_id = detection[6] if len(detection) > 6 else -1
                    detection = {
                        "x": x,
                        "y": y,
                        "width": w,
                        "height": h,
                        "confidence": conf,
                        "class_id": class_id,
                        "id": track_id,
                        "center_x": x + w/2,
                        "center_y": y + h/2
                    }
                
                # Get width and height attributes or calculate from x/y/w/h values
                width = detection.get("width", 0)
                height = detection.get("height", 0)
                area = width * height
                
                if area > max_area:
                    max_area = area
                    best_detection = detection
                    
            return best_detection
        
        return None
    
    def release(self):
        """Release resources."""
        self.stop_tracking()
        # Don't disconnect since other services might be using the servo service
        self.logger.info("PBVS Service resources released")
    
    def set_balloon_detector(self, balloon_detector):
        """Set balloon detector to get detections from."""
        self.balloon_detector = balloon_detector
        self.logger.info("Balloon detector connected to PBVS service")
        
    def set_detections(self, detections):
        """Store detections provided by the camera service."""
        # Store the detections temporarily for use in drawing and tracking
        self.last_detections = detections
    
    def draw_tracking_visualization(self, frame, target_detection=None):
        """Draw tracking visualization on frame."""
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
        
        # If we have a current target point, draw it
        if self.current_image_point:
            tx, ty = self.current_image_point
            
            # Draw target crosshair
            cv2.drawMarker(vis_frame, (int(tx), int(ty)), 
                         (0, 0, 255), markerType=cv2.MARKER_CROSS, 
                         markerSize=20, thickness=2)
                         
            # Draw line from center to target
            cv2.line(vis_frame, (self.center_x, self.center_y), 
                   (int(tx), int(ty)), (0, 165, 255), 2)
            
            # Draw estimated depth
            depth_text = f"Z: {self.Z:.2f}m"
            cv2.putText(vis_frame, depth_text, (int(tx) + 10, int(ty) - 10),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                      
            # Draw angles
            if self.desired_pan is not None and self.desired_tilt is not None:
                angle_text = f"Pan: {self.desired_pan:.1f}° Tilt: {self.desired_tilt:.1f}°"
                cv2.putText(vis_frame, angle_text, (int(tx) + 10, int(ty) + 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
        
        # Draw tracking stats
        stats = self.get_error_stats()
        cv2.putText(vis_frame, f"PBVS Tracking", (10, 30),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                  
        cv2.putText(vis_frame, f"Err: {stats['current']} px", (10, 60),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 1)
        
        return vis_frame 