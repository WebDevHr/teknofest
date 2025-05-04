#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YOLO Detection Service
---------------------
Service for handling object detection using YOLO model.
"""

import cv2
import numpy as np
import os
import torch
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService
from ultralytics import YOLO
from collections import defaultdict

class YoloService(QObject):
    """
    Service for handling object detection using YOLO model.
    """
    # Signals
    detection_ready = pyqtSignal(object, list)  # frame, detections
    
    def __init__(self, model_path="C:\\Users\\Administrator\\Desktop\\gok-2025\\teknofest\\camera_app\\models\\bests_balloon_30_dark.pt"):
        super().__init__()
        self.logger = LoggerService()
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
        
        # Daha geniş bir sınıf listesi oluşturalım veya modelden alalım
        self.class_names = ["balon"]  # Varsayılan

        # Tracking related variables
        self.track_history = defaultdict(lambda: [])
        self.max_track_history = 30
        
        # Performans için ek ayarlar
        self.last_frame_detections = []
        self.skip_frames = 0
        self.max_skip_frames = 1  # Her 2 karede bir tespit yap
        
    def initialize(self, model_path=None):
        """Initialize the YOLO model."""
        if model_path:
            self.model_path = model_path
            
        if not self.model_path or not os.path.exists(self.model_path):
            self.logger.error(f"YOLO model not found at: {self.model_path}")
            return False
            
        try:
            # Cihaz seçimi - GPU varsa GPU, yoksa CPU kullan
            device = 0 if self.use_gpu else 'cpu'  # 0 = ilk GPU
            
            # YOLOv8 modelini yükle - ByteTrack için adres belirt
            self.model = YOLO(self.model_path)
            
            # Model cihazını ayarla
            self.model.to(device)
            
            # Modelin sınıf isimlerini al
            self.class_names = self.model.names
            
            # Log success
            self.logger.info(f"YOLO modeli yüklendi: {self.model_path}, Cihaz: {device}")
            self.is_initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to load YOLO model: {str(e)}")
            return False
    
    def start(self):
        """Start the detection service."""
        if not self.is_initialized:
            self.logger.error("YOLO model not initialized")
            return False
            
        self.is_running = True
        self.skip_frames = 0
        # Log
        self.logger.info("YOLO algılama servisi başlatıldı")
        return True
    
    def stop(self):
        """Stop the detection service."""
        self.is_running = False
        # Track geçmişini temizle
        self.track_history.clear()
        # Log
        self.logger.info("YOLO algılama servisi durduruldu")
    
    def detect(self, frame):
        """
        Detect objects in a frame and track them.
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            List of detections, each containing [x, y, w, h, confidence, class_id, track_id]
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
            
            # YOLOv8 ile tespit yap, ByteTrack kullanarak
            results = self.model.track(
                frame, 
                persist=True, 
                tracker="bytetrack.yaml", 
                verbose=False, 
                conf=0.25,  # Güven eşiği - düşük değer daha fazla tespit (ama yanlış pozitif olabilir)
                iou=0.45,   # IOU eşiği - kutuların çakışması için
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
            self.logger.error(f"Error during detection and tracking: {str(e)}")
            return []
    
    def _process_results(self, results, frame_shape):
        """Process YOLOv8 results to get detections and tracking info."""
        detections = []
        
        # Sonuçları işle
        for result in results:
            if result.boxes is None or len(result.boxes) == 0:
                continue
                
            boxes = result.boxes
            
            # Track IDs varsa al
            track_ids = []
            if hasattr(boxes, 'id') and boxes.id is not None:
                track_ids = boxes.id.int().cpu().tolist()
            
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
                
                # Track ID (varsa ekle)
                track_id = -1
                if i < len(track_ids):
                    track_id = track_ids[i]
                    
                    # Track history'yi güncelle
                    track = self.track_history[track_id]
                    # Merkezi bul
                    center_x = float(x1 + w / 2)
                    center_y = float(y1 + h / 2)
                    track.append((center_x, center_y))
                    
                    # Track history'yi sınırla
                    if len(track) > self.max_track_history:
                        track.pop(0)
                
                # Tespit listesine ekle [x, y, w, h, confidence, class_id, track_id]
                detections.append([int(x1), int(y1), int(w), int(h), float(confidence), class_id, track_id])
        
        return detections
    
    def draw_detections(self, frame, detections):
        """Draw detection boxes, tracking IDs, and confidence values on the frame."""
        # If no detections, return the original frame without any overlay
        if not detections:
            return frame
            
        # Create a black mask for the entire frame (for opacity overlay)
        height, width = frame.shape[:2]
        mask = np.zeros((height, width), dtype=np.uint8)
        
        # Mark balloon regions in the mask
        for detection in detections:
            x, y, w, h, confidence, class_id, track_id = detection
            
            # Ensure coordinates are within frame boundaries
            x = max(0, x)
            y = max(0, y)
            x2 = min(width, x + w)
            y2 = min(height, y + h)
            
            # Check if this is a balloon class
            class_name = "unknown"
            if class_id < len(self.class_names):
                class_name = self.class_names[class_id]
            
            # Mark all detected regions in the mask, not just balloons
            mask[y:y2, x:x2] = 255
        
        # Create a semi-transparent black overlay
        overlay = frame.copy()
        # Apply black color on the regions that are not inside bounding boxes (where mask is 0)
        overlay[mask == 0] = [0, 0, 0]  # Black color
        
        # Blend the original frame with the overlay
        alpha = 0.2  # 20% of original image (80% opacity for black overlay)
        frame = cv2.addWeighted(overlay, 1-alpha, frame, alpha, 0)
        
        # Now draw boxes and labels on the frame
        for detection in detections:
            x, y, w, h, confidence, class_id, track_id = detection
            
            # Sınırları kontrol et
            x = max(0, x)
            y = max(0, y)
            
            # Dikdörtgen çiz
            color = (0, 255, 0)  # Yeşil
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Sınıf adını güvenli bir şekilde al
            class_name = "unknown"
            if class_id < len(self.class_names):
                class_name = self.class_names[class_id]
            
            # Etiket metni - şimdi ID de içeriyor
            label = f"{class_name}: {confidence:.2f}"
            if track_id >= 0:
                label = f"{class_name} ID:{track_id}: {confidence:.2f}"
            
            # Etiket arkaplanı
            text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.rectangle(frame, (x, y - 20), (x + text_size[0], y), color, -1)
            
            # Etiket metni
            cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
            # Track çizgisini çiz (track_id varsa)
            if track_id >= 0 and track_id in self.track_history and len(self.track_history[track_id]) > 1:
                track = self.track_history[track_id]
                # Track'in noktalarını numpy dizisine dönüştür
                points = np.array(track, dtype=np.int32).reshape((-1, 1, 2))
                # Tracking çizgisini çiz
                cv2.polylines(frame, [points], isClosed=False, color=(230, 230, 230), thickness=2)
            
        return frame 