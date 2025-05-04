#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mock Detection Service
---------------------
Simple mock service for non-implemented detection methods.
"""

import cv2
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService

class MockService(QObject):
    """
    Mock service for handling non-implemented detection methods.
    Simply passes through frames without any detection.
    """
    # Signals
    detection_ready = pyqtSignal(object, list)  # frame, detections
    
    def __init__(self, service_name="Mock Service"):
        super().__init__()
        self.logger = LoggerService()
        self.is_initialized = True
        self.is_running = False
        self.service_name = service_name
        
    def initialize(self):
        """Initialize the mock service."""
        self.is_initialized = True
        self.logger.info(f"{self.service_name} başlatıldı")
        return True
    
    def start(self):
        """Start the detection service."""
        self.is_running = True
        self.logger.info(f"{self.service_name} detection servisi başlatıldı")
        return True
    
    def stop(self):
        """Stop the detection service."""
        self.is_running = False
        self.logger.info(f"{self.service_name} detection servisi durduruldu")
    
    def detect(self, frame):
        """
        Simply pass through the frame without detection.
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            Empty list of detections
        """
        if not self.is_running:
            return []
            
        # Just pass through the frame with no detections
        self.detection_ready.emit(frame, [])
        return []
    
    def draw_detections(self, frame, detections):
        """No detections to draw, just return the original frame."""
        return frame 