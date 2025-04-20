#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Roboflow Detection Service
---------------------
Service for handling object detection using Roboflow model.
"""

import cv2
import numpy as np
import os
import torch
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService
from ultralytics import YOLO

class RoboflowService(QObject):
    """
    Service for handling object detection using Roboflow model.
    """
    # Signals
    detection_ready = pyqtSignal(object, list)  # frame, detections
    
    def __init__(self, model_path="models/engagement-best.pt"):
        super().__init__()
        self.logger = LoggerService()
        self.model_path = model_path
        self.model = None
        self.is_initialized = False
        self.is_running = False
        self.class_names = []  # Varsayılan
        
    def initialize(self, model_path=None):
        """Initialize the Roboflow model."""
        if model_path:
            self.model_path = model_path
            
        if not self.model_path or not os.path.exists(self.model_path):
            self.logger.error(f"Roboflow model not found at: {self.model_path}")
            return False
            
        try:
            # Roboflow modelini yükle (YOLOv8 tabanlı)
            self.model = YOLO(self.model_path)
            
            # Modelin sınıf isimlerini al
            self.class_names = self.model.names
            
            self.logger.info(f"Roboflow model loaded from: {self.model_path}")
            self.is_initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to load Roboflow model: {str(e)}")
            return False
    
    def start(self):
        """Start the detection service."""
        if not self.is_initialized:
            self.logger.error("Roboflow model not initialized")
            return False
            
        self.is_running = True
        self.logger.info("Roboflow detection service started")
        return True
    
    def stop(self):
        """Stop the detection service."""
        self.is_running = False
        self.logger.info("Roboflow detection service stopped")
    
    def detect(self, frame):
        """
        Detect objects in a frame.
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            List of detections, each containing [x, y, w, h, confidence, class_id]
        """
        if not self.is_initialized or not self.is_running:
            return []
            
        try:
            # Roboflow ile tespit yap
            results = self.model(frame, verbose=False)
            
            # Sonuçları işle
            detections = self._process_results(results, frame.shape)
            
            # Sinyali gönder
            self.detection_ready.emit(frame, detections)
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Error during detection: {str(e)}")
            return []
    
    def _process_results(self, results, frame_shape):
        """Process Roboflow results to get detections."""
        detections = []
        
        # Sonuçları işle
        for result in results:
            boxes = result.boxes
            
            for box in boxes:
                # Kutu koordinatları
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                # Genişlik ve yükseklik hesapla
                w = x2 - x1
                h = y2 - y1
                
                # Güven değeri
                confidence = box.conf[0].cpu().numpy()
                
                # Sınıf ID
                class_id = int(box.cls[0].cpu().numpy())
                
                # Tespit listesine ekle [x, y, w, h, confidence, class_id]
                detections.append([int(x1), int(y1), int(w), int(h), float(confidence), class_id])
        
        return detections
    
    def draw_detections(self, frame, detections):
        """Draw detection boxes on the frame."""
        for detection in detections:
            x, y, w, h, confidence, class_id = detection
            
            # Sınırları kontrol et
            x = max(0, x)
            y = max(0, y)
            
            # Dikdörtgen çiz
            color = (0, 255, 255)  # Sarı
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Sınıf adını güvenli bir şekilde al
            class_name = "unknown"
            if class_id < len(self.class_names):
                class_name = self.class_names[class_id]
            
            # Etiket metni
            label = f"{class_name}: {confidence:.2f}"
            
            # Etiket arkaplanı
            text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.rectangle(frame, (x, y - 20), (x + text_size[0], y), color, -1)
            
            # Etiket metni
            cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
        return frame 