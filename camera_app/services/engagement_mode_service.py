#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Engagement Mode Service
---------------------
Service for detecting shapes/colors using YOLO model.
For 3. Aşama - Angajman Mode (Derin Öğrenmeli)
"""

import cv2
import numpy as np
import os
import torch
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService
from ultralytics import YOLO

class EngagementModeService(QObject):
    """
    Service for handling engagement mode detection using YOLO model.
    Detects 9 shape/color combinations: red-circle, red-square, red-triangle,
    blue-circle, blue-square, blue-triangle, green-circle, green-square, green-triangle.
    """
    # Signals
    detection_ready = pyqtSignal(object, list)  # frame, detections
    
    def __init__(self, model_path=None):
        super().__init__()
        self.logger = LoggerService()
        
        # Set default model path if not provided
        if model_path is None:
            self.model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                         "models", "engagement-best.pt")
        else:
            self.model_path = model_path
            
        self.model = None
        self.is_initialized = False
        self.is_running = False
        
        # GPU kontrolü
        self.use_gpu = torch.cuda.is_available()
        if self.use_gpu:
            self.logger.info("GPU kullanılabilir - CUDA desteği aktif")
        else:
            self.logger.info("GPU kullanılamıyor - CPU kullanılacak")
        
        # Default class names for engagement mode
        self.class_names = ["red-circle", "red-square", "red-triangle", 
                           "blue-circle", "blue-square", "blue-triangle", 
                           "green-circle", "green-square", "green-triangle"]

        # Performans için ek ayarlar
        self.last_frame_detections = []
        self.skip_frames = 0
        self.max_skip_frames = 1  # Her 2 karede bir tespit yap
        
    def initialize(self, model_path=None):
        """Initialize the YOLO model."""
        if model_path:
            self.model_path = model_path
            
        if not self.model_path or not os.path.exists(self.model_path):
            self.logger.error(f"Angajman dedektör model dosyası bulunamadı: {self.model_path}")
            return False
            
        try:
            # Cihaz seçimi - GPU varsa GPU, yoksa CPU kullan
            device = 0 if self.use_gpu else 'cpu'  # 0 = ilk GPU
            
            # YOLOv8 modelini yükle
            self.model = YOLO(self.model_path)
            
            # Model cihazını ayarla
            self.model.to(device)
            
            # Modelin sınıf isimlerini al
            self.class_names = self.model.names
            
            # Log success
            self.logger.info(f"Angajman dedektör modeli yüklendi: {self.model_path}, Cihaz: {device}")
            self.is_initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Angajman dedektör modeli yüklenemedi: {str(e)}")
            return False
    
    def start(self):
        """Start the detection service."""
        if not self.is_initialized:
            self.logger.error("Angajman dedektör modeli initialize edilmedi")
            return False
            
        self.is_running = True
        self.skip_frames = 0
        # Log
        self.logger.info("Angajman dedektör servisi başlatıldı")
        return True
    
    def stop(self):
        """Stop the detection service."""
        self.is_running = False
        # Log
        self.logger.info("Angajman dedektör servisi durduruldu")
    
    def detect(self, frame):
        """
        Detect shapes and colors in a frame.
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            List of detections, each containing [x, y, w, h, confidence, class_id]
        """
        if not self.is_initialized or not self.is_running:
            return []
        
        # Frame skip stratejisi - her max_skip_frames'de bir tespit yap
        self.skip_frames += 1
        if self.skip_frames <= self.max_skip_frames and len(self.last_frame_detections) > 0:
            # Son tespit edilen nesneleri geri döndür
            return self.last_frame_detections
        
        # Sıfırla
        self.skip_frames = 0
            
        try:
            # Performans için en iyi ayarlar
            half = self.use_gpu  # GPU kullanıyorsa half precision kullan
            
            # Resmi daha küçük boyutlara getir (640x640 veya 320x320 gibi)
            # Orijinal en-boy oranını koru ama tespit için daha küçük boyut kullan
            img_size = 320 if self.use_gpu else 640  # GPU varsa daha düşük çözünürlük yeterli olabilir
            
            # YOLOv8 ile tespit yap
            results = self.model(
                frame, 
                verbose=False, 
                conf=0.25,  # Güven eşiği
                iou=0.45,   # IOU eşiği
                half=half,  # Half precision için
                imgsz=img_size,  # Resim boyutu
                max_det=20,  # Maksimum tespit sayısı
            )
            
            # Sonuçları işle
            detections = self._process_results(results, frame.shape)
            
            # Sinyali gönder
            self.detection_ready.emit(frame, detections)
            
            # Son tespitleri sakla
            self.last_frame_detections = detections
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Angajman tespiti sırasında hata: {str(e)}")
            return []
    
    def _process_results(self, results, frame_shape):
        """Process YOLOv8 results to get detections."""
        detections = []
        
        # Sonuçları işle
        for result in results:
            if result.boxes is None or len(result.boxes) == 0:
                continue
                
            boxes = result.boxes
            
            for i, box in enumerate(boxes):
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
        """Draw detection boxes on the frame with transparent overlay."""
        if not detections:
            return frame
            
        # Work on a copy of the frame
        output = frame.copy()
        
        # Create a mask for all shape detections
        height, width = frame.shape[:2]
        mask = np.zeros((height, width), dtype=np.uint8)
        
        # Mark all detected regions in the mask
        for detection in detections:
            x, y, w, h = detection[:4]
            
            # Make sure coordinates are valid
            x = max(0, int(x))
            y = max(0, int(y))
            x2 = min(width, x + int(w))
            y2 = min(height, y + int(h))
            
            # Fill the detected region in the mask
            mask[y:y2, x:x2] = 255
        
        # Create a semi-transparent black overlay
        overlay = frame.copy()
        # Apply black color on the regions that are not inside detection bounding boxes (where mask is 0)
        overlay[mask == 0] = [0, 0, 0]  # Black color
        
        # Blend the original frame with the overlay
        alpha = 0.3  # 30% of original image (70% opacity for black overlay)
        output = cv2.addWeighted(overlay, 1-alpha, frame, alpha, 0)
        
        # Colors for engagement shapes/colors (9 classes)
        engagement_colors = {
            'red-circle': (0, 0, 255),     # Red
            'red-square': (0, 0, 255),     # Red
            'red-triangle': (0, 0, 255),   # Red
            'blue-circle': (255, 0, 0),    # Blue
            'blue-square': (255, 0, 0),    # Blue
            'blue-triangle': (255, 0, 0),  # Blue
            'green-circle': (0, 255, 0),   # Green
            'green-square': (0, 255, 0),   # Green
            'green-triangle': (0, 255, 0)  # Green
        }
        
        # Draw each detection
        for detection in detections:
            x, y, w, h, conf, class_id = detection[:6]
            
            # Get class name
            class_name = "unknown"
            if class_id < len(self.class_names):
                class_name = self.class_names[class_id]
            
            # Choose color based on class name
            color = (0, 255, 0)  # Default green
            if class_name in engagement_colors:
                color = engagement_colors[class_name]
            
            # Draw rectangle around detected object
            cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
            
            # Prepare label text with confidence
            label = f"{class_name}: {conf:.2f}"
            
            # Draw label background
            text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(output, (x, y - 20), (x + text_size[0], y), color, -1)
            
            # Draw label text (with black color for better visibility)
            cv2.putText(output, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        return output 