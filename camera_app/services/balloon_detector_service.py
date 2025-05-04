#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Balloon Detector Service
---------------------
Service for detecting balloons using YOLO model.
For 1. Aşama - Hareketli Balon Mode (Derin Öğrenmeli)
"""

import cv2
import numpy as np
import os
import torch
import time
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService
from services.kalman_filter_service import KalmanFilterService
from ultralytics import YOLO
from collections import defaultdict

class BalloonDetectorService(QObject):
    """
    Service for detecting balloons using YOLO model.
    """
    # Signals
    detection_ready = pyqtSignal(object, list)  # frame, detections
    
    def __init__(self, model_path=None):
        super().__init__()
        self.logger = LoggerService()
        
        # Set default model path if not provided
        if model_path is None:
            self.model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                          "models", "bests_balloon_30_dark.pt")
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
        
        # Balloon class name
        self.class_names = ["balon"]  # Varsayılan

        # Tracking related variables
        self.track_history = defaultdict(lambda: [])
        self.max_track_history = 30
        
        # Track'lerin son görülme zamanını tutacak dictionary
        self.last_seen_time = {}
        self.track_timeout = 0.5  # Tracks will be removed after this many seconds of not being seen
        
        # Performans için ek ayarlar
        self.last_frame_detections = []
        self.skip_frames = 0
        self.max_skip_frames = 1  # Her 2 karede bir tespit yap
        
        # Kalman Filter Service
        self.kalman_service = KalmanFilterService()
        self.use_kalman = True  # Whether to use Kalman filtering
        self.show_kalman_debug = True  # Whether to show Kalman debug visualization
        
        # Frame and timing information
        self.frame_count = 0
        self.current_frame_id = None
        
    def initialize(self, model_path=None):
        """Initialize the YOLO model."""
        if model_path:
            self.model_path = model_path
            
        if not self.model_path or not os.path.exists(self.model_path):
            self.logger.error(f"Balon dedektör model dosyası bulunamadı: {self.model_path}")
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
            self.logger.info(f"Balon dedektör modeli yüklendi: {self.model_path}, Cihaz: {device}")
            self.is_initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Balon dedektör modeli yüklenemedi: {str(e)}")
            return False
    
    def start(self):
        """Start the detection service."""
        if not self.is_initialized:
            self.logger.error("Balon dedektör modeli initialize edilmedi")
            return False
            
        self.is_running = True
        self.skip_frames = 0
        # Log
        self.logger.info("Balon dedektör servisi başlatıldı")
        return True
    
    def stop(self):
        """Stop the detection service."""
        self.is_running = False
        # Track geçmişini temizle
        self.track_history.clear()
        self.last_seen_time.clear()
        # Log
        self.logger.info("Balon dedektör servisi durduruldu")
    
    def detect(self, frame):
        """
        Detect balloons in a frame and track them.
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            List of detections, each containing [x, y, w, h, confidence, class_id, track_id]
        """
        if not self.is_initialized or not self.is_running:
            return []
        
        # Create a unique ID for this frame and mark it as received
        self.frame_count += 1
        self.current_frame_id = f"frame_{self.frame_count}_{time.time()}"
        frame_time = time.time()
        
        if self.use_kalman:
            self.kalman_service.mark_frame_received(self.current_frame_id)
        
        # Frame skip stratejisi - her max_skip_frames'de bir tespit yap
        self.skip_frames += 1
        if self.skip_frames <= self.max_skip_frames and len(self.last_frame_detections) > 0:
            # Son tespit edilen nesneleri geri döndür
            return self.last_frame_detections
        
        # Sıfırla
        self.skip_frames = 0
        
        # Zaman aşımına uğrayan track'leri temizle
        self._remove_stale_tracks(frame_time)
            
        try:
            if self.use_kalman:
                self.kalman_service.mark_processing_start(self.current_frame_id)
                
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
            detections = self._process_results(results, frame.shape, frame_time)
            
            # Kalman filter için işlem sonu işaretle
            if self.use_kalman:
                self.kalman_service.mark_processing_end(self.current_frame_id)
            
            # Sinyali gönder
            self.detection_ready.emit(frame, detections)
            
            # Son tespitleri sakla
            self.last_frame_detections = detections
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Balon tespiti ve izleme sırasında hata: {str(e)}")
            # Hata durumunda da Kalman işlem sonu işaretle
            if self.use_kalman:
                self.kalman_service.mark_processing_end(self.current_frame_id)
            return []
    
    def _remove_stale_tracks(self, current_time):
        """Belirli bir süre görünmediğinde track'leri temizle."""
        # Track'leri kontrol et ve eski olanları temizle
        stale_track_ids = []
        for track_id, last_time in self.last_seen_time.items():
            if current_time - last_time > self.track_timeout:
                stale_track_ids.append(track_id)
                
        # Stale track'leri temizle
        for track_id in stale_track_ids:
            if track_id in self.track_history:
                del self.track_history[track_id]
            if track_id in self.last_seen_time:
                del self.last_seen_time[track_id]
            # Kalman filtresini de temizle
            if self.use_kalman:
                self.kalman_service.remove_track(track_id)
        
        # Ayrıca Kalman filtresi servisinde de temizlik yap
        if self.use_kalman:
            self.kalman_service.cleanup_old_tracks(max_age_seconds=self.track_timeout)
            
        return stale_track_ids
    
    def _process_results(self, results, frame_shape, frame_time=None):
        """Process YOLOv8 results to get detections and tracking info."""
        detections = []
        current_time = time.time()
        
        # Mevcut karede görülen track ID'leri kaydet
        current_track_ids = set()
        
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
                
                # Merkez noktası
                center_x = float(x1 + w / 2)
                center_y = float(y1 + h / 2)
                
                # Güven değeri
                confidence = box.conf[0].cpu().numpy()
                
                # Sınıf ID
                class_id = int(box.cls[0].cpu().numpy())
                
                # Track ID (varsa ekle)
                track_id = -1
                if i < len(track_ids):
                    track_id = track_ids[i]
                    
                    # Bu track ID'yi mevcut görülen ID'ler listesine ekle
                    current_track_ids.add(track_id)
                    
                    # Son görülme zamanını güncelle
                    self.last_seen_time[track_id] = current_time
                    
                    # Track history'yi güncelle
                    track = self.track_history[track_id]
                    track.append((center_x, center_y))
                    
                    # Track history'yi sınırla
                    if len(track) > self.max_track_history:
                        track.pop(0)
                    
                    # Kalman filtresi güncelle
                    if self.use_kalman and track_id != -1:
                        # Update Kalman filter with the current position
                        self.kalman_service.update(track_id, (center_x, center_y), frame_time)
                        
                        # Get prediction for the position after system delay
                        predicted_pos = self.kalman_service.predict(track_id)
                        
                        if predicted_pos:
                            # Adjust detection with predicted position
                            pred_x, pred_y = predicted_pos
                            
                            # Calculate offset from current center to predicted center
                            offset_x = pred_x - center_x
                            offset_y = pred_y - center_y
                            
                            # Apply offset to the bounding box
                            x1 += offset_x
                            y1 += offset_y
                            x2 += offset_x
                            y2 += offset_y
                            
                            # Recalculate width, height, and center
                            w = x2 - x1
                            h = y2 - y1
                            center_x = pred_x
                            center_y = pred_y
                
                # Tespit listesine ekle [x, y, w, h, confidence, class_id, track_id]
                detections.append([int(x1), int(y1), int(w), int(h), float(confidence), class_id, track_id])
        
        return detections
    
    def draw_detections(self, frame, detections):
        """Draw detection boxes and tracking lines on the frame."""
        if not detections:
            return frame
            
        # Work on a copy of the frame
        output = frame.copy()
        
        # Create a mask for the balloon detections (to create a dark transparent overlay)
        height, width = frame.shape[:2]
        mask = np.zeros((height, width), dtype=np.uint8)
        
        # Mark balloon regions in the mask
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
        # Apply black color on the regions that are not inside balloon bounding boxes (where mask is 0)
        overlay[mask == 0] = [0, 0, 0]  # Black color
        
        # Blend the original frame with the overlay
        alpha = 0.3  # 30% of original image (70% opacity for black overlay)
        output = cv2.addWeighted(overlay, 1-alpha, frame, alpha, 0)
        
        # Default color for balloons
        color = (0, 255, 0)  # Green
        
        # Draw each detection
        for detection in detections:
            if len(detection) >= 6:
                x, y, w, h, conf, class_id = detection[:6]
                track_id = detection[6] if len(detection) > 6 else -1
                
                # Draw rectangle around detected object
                cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
                
                # Get class name
                class_name = "unknown"
                if class_id < len(self.class_names):
                    class_name = self.class_names[class_id]
                
                # Prepare label text with confidence
                label = f"{class_name}: {conf:.2f}"
                if track_id != -1:
                    label += f" ID:{track_id}"
                
                # Draw label background
                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                cv2.rectangle(output, (x, y - 20), (x + text_size[0], y), color, -1)
                
                # Draw label text (with black color for better visibility)
                cv2.putText(output, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                
                # Draw tracking lines if track_id is available
                if track_id != -1 and track_id in self.track_history:
                    track = self.track_history[track_id]
                    
                    # Draw the tracking line
                    if len(track) > 1:
                        # Draw lines connecting previous positions
                        points = np.array(track, dtype=np.int32).reshape((-1, 1, 2))
                        cv2.polylines(output, [points], False, color, 1)
        
        # Add Kalman filter debug visualization if enabled
        if self.use_kalman and self.show_kalman_debug:
            output = self.kalman_service.draw_debug(output)
        
        # Draw crosshair at the center of the frame
        center_x = width // 2
        center_y = height // 2
        
        # Set crosshair properties
        crosshair_color = (0, 0, 255)  # Kırmızı (BGR formatında)
        crosshair_size = 20
        crosshair_thickness = 2
        
        # Draw horizontal line of the crosshair
        cv2.line(output, 
                (center_x - crosshair_size, center_y), 
                (center_x + crosshair_size, center_y), 
                crosshair_color, 
                crosshair_thickness)
        
        # Draw vertical line of the crosshair
        cv2.line(output, 
                (center_x, center_y - crosshair_size), 
                (center_x, center_y + crosshair_size), 
                crosshair_color, 
                crosshair_thickness)
        
        # Draw a small circle at the center for better visibility
        cv2.circle(output, 
                 (center_x, center_y), 
                 2, 
                 crosshair_color, 
                 -1)  # -1 thickness means filled circle
        
        return output 