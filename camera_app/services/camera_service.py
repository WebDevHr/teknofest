#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Camera Service
-------------
Service for handling camera operations.
"""

import cv2
import os
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QImage
from services.logger_service import LoggerService

class CameraService(QObject):
    """
    Service for handling camera operations.
    Implements the Observer pattern with signals.
    """
    # Signals
    frame_ready = pyqtSignal(QImage)
    camera_error = pyqtSignal(str)
    
    def __init__(self, camera_id=0):
        super().__init__()
        self.logger = LoggerService()
        self.camera_id = camera_id
        self.capture = None
        self.timer = None
        self.is_running = False
        
    def initialize(self):
        """Initialize the camera."""
        self.capture = cv2.VideoCapture(self.camera_id)
        
        if not self.capture.isOpened():
            error_msg = f"Could not open camera with ID {self.camera_id}"
            self.logger.error(error_msg)
            self.camera_error.emit(error_msg)
            return False
        
        self.logger.info(f"Camera initialized successfully (ID: {self.camera_id})")
        return True
    
    def start(self, fps=30):
        """Start capturing frames at the specified FPS."""
        if not self.capture or not self.capture.isOpened():
            if not self.initialize():
                return False
        
        # Create and start timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._process_frame)
        interval = int(1000 / fps)  # Convert FPS to milliseconds
        self.timer.start(interval)
        
        self.is_running = True
        self.logger.info(f"Camera started at {fps} FPS")
        return True
    
    def stop(self):
        """Stop capturing frames."""
        if self.timer:
            self.timer.stop()
            
        self.is_running = False
        self.logger.info("Camera stopped")
    
    def release(self):
        """Release camera resources."""
        self.stop()
        
        if self.capture:
            self.capture.release()
            self.capture = None
            self.logger.info("Camera resources released")
    
    def _process_frame(self):
        """Process a frame from the camera."""
        if not self.capture or not self.capture.isOpened():
            self.camera_error.emit("Camera not available")
            self.stop()
            return
            
        ret, frame = self.capture.read()
        if ret:
            # Kare sayacını artır
            if not hasattr(self, 'frame_count'):
                self.frame_count = 0
            self.frame_count += 1
            
            # Şekil tespiti aktifse, tespit işlemini yap
            if hasattr(self, 'shape_detection_service') and self.shape_detection_service.is_running:
                # Tespit işlemi
                shapes = self.shape_detection_service.detect(frame, self.frame_count)
                
                # Şekil tespiti sonrası frame güncellenmiş olabilir, o yüzden yeni frame'i alalım
                if hasattr(self.shape_detection_service, 'processed_frame'):
                    frame = self.shape_detection_service.processed_frame
            
            # YOLO tespiti aktifse, tespit işlemini yap
            if hasattr(self, 'yolo_service') and self.yolo_service.is_running:
                # Tespit işlemi
                detections = self.yolo_service.detect(frame)
                
                # Tespitleri çiz
                frame = self.yolo_service.draw_detections(frame, detections)
            
            # Roboflow tespiti aktifse, tespit işlemini yap
            if hasattr(self, 'roboflow_service') and self.roboflow_service.is_running:
                # Tespit işlemi
                detections = self.roboflow_service.detect(frame)
                
                # Tespitleri çiz
                frame = self.roboflow_service.draw_detections(frame, detections)
            
            # Convert the frame to RGB format
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Get frame dimensions
            height, width, channels = rgb_frame.shape
            
            # Create QImage from frame
            bytes_per_line = channels * width
            q_image = QImage(rgb_frame.data.tobytes(), width, height, bytes_per_line, QImage.Format_RGB888).copy()
            
            # Emit the frame
            self.frame_ready.emit(q_image)
        else:
            self.camera_error.emit("Error capturing frame")
    
    def capture_image(self, directory="captures"):
        """Capture and save the current frame."""
        if not self.capture or not self.capture.isOpened():
            self.logger.error("Cannot capture: Camera not available")
            return None
            
        # Create directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{directory}/capture_{timestamp}.png"
        
        # Capture frame
        ret, frame = self.capture.read()
        if ret:
            # Save the image
            cv2.imwrite(filename, frame)
            self.logger.info(f"Image captured and saved as {filename}")
            return filename
        else:
            self.logger.error("Failed to capture image")
            return None
    
    def set_yolo_service(self, yolo_service):
        """Set the YOLO service for object detection."""
        self.yolo_service = yolo_service
        self.logger.info("YOLO service connected to camera")
    
    def set_shape_detection_service(self, shape_detection_service):
        """Set the shape detection service."""
        self.shape_detection_service = shape_detection_service
        self.logger.info("Shape detection service connected to camera")
    
    def set_roboflow_service(self, roboflow_service):
        """Set the Roboflow service for object detection."""
        self.roboflow_service = roboflow_service
        self.logger.info("Roboflow service connected to camera") 