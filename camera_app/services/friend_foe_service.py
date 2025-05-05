#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Friend/Foe Detector Service
---------------------
Service for detecting friends and foes using YOLO model.
For 2. Aşama - Hareketli Dost/Düşman Mode (Derin Öğrenmeli)
"""

import cv2
import numpy as np
import os
import torch
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService
from ultralytics import YOLO
from collections import defaultdict
import time

class FriendFoeService(QObject):
    """
    Service for detecting friend and foe objects using YOLO model.
    """
    # Signals
    detection_ready = pyqtSignal(object, list)  # frame, detections
    
    def __init__(self, model_path=None):
        super().__init__()
        self.logger = LoggerService()
        
        # Set default model path if not provided
        if model_path is None:
            self.model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                         "models", "friend_foe(v8n).pt")
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
        
        # Friend/Foe class names
        self.class_names = ["dost", "dusman"]  # Varsayılan

        # Performans için ek ayarlar
        self.last_frame_detections = []
        self.skip_frames = 0
        self.max_skip_frames = 1  # Her 2 karede bir tespit yap
        
        # Tracking related variables
        self.track_history = defaultdict(lambda: [])
        self.max_track_history = 30
        
        # FPS calculation
        self.fps = 0  # Current FPS
        self.fps_update_interval = 1.0  # Update FPS every 1 second
        self.last_fps_update_time = time.time()
        self.frame_times = []  # Store frame timestamps for FPS calculation
        self.processed_frames = 0  # Total processed frames (cumulative)
        self.ibvs_processed_frames = 0  # Total frames sent to IBVS (cumulative)
        
        # FPS calculation for different stats
        self.frame_times_total = []  # For total FPS calculation
        self.frame_times_ibvs = []  # For IBVS FPS calculation  
        self.total_fps = 0  # FPS for total frames
        self.ibvs_fps = 0  # FPS for IBVS frames
        
    def initialize(self, model_path=None):
        """Initialize the YOLO model."""
        if model_path:
            self.model_path = model_path
            
        if not self.model_path or not os.path.exists(self.model_path):
            self.logger.error(f"Dost/Düşman dedektör model dosyası bulunamadı: {self.model_path}")
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
            self.logger.info(f"Dost/Düşman dedektör modeli yüklendi: {self.model_path}, Cihaz: {device}")
            self.is_initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Dost/Düşman dedektör modeli yüklenemedi: {str(e)}")
            return False
    
    def start(self):
        """Start the detection service."""
        if not self.is_initialized:
            self.logger.error("Dost/Düşman dedektör modeli initialize edilmedi")
            return False
            
        self.is_running = True
        self.skip_frames = 0
        # Log
        self.logger.info("Dost/Düşman dedektör servisi başlatıldı")
        return True
    
    def stop(self):
        """Stop the detection service."""
        self.is_running = False
        # Log
        self.logger.info("Dost/Düşman dedektör servisi durduruldu")
    
    def detect(self, frame):
        """
        Detect friend/foe objects in a frame.
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            List of detections, each containing [x, y, w, h, confidence, class_id, track_id]
        """
        if not self.is_initialized or not self.is_running:
            return []
        
        # Update processed frames count
        self.processed_frames += 1
        
        # FPS ve frame zamanlarını güncelle
        frame_time = time.time()
        
        # Add frame time for FPS calculation
        self.frame_times.append(frame_time)
        
        # Add frame time for Total FPS calculation
        self.frame_times_total.append(frame_time)
        
        # Clean old frame times (older than 1 second)
        current_time = time.time()
        while self.frame_times and (current_time - self.frame_times[0] > 1.0):
            self.frame_times.pop(0)
        
        # Clean old total frame times (older than 1 second)
        while self.frame_times_total and (current_time - self.frame_times_total[0] > 1.0):
            self.frame_times_total.pop(0)
            
        # Clean old IBVS frame times (older than 1 second)
        while self.frame_times_ibvs and (current_time - self.frame_times_ibvs[0] > 1.0):
            self.frame_times_ibvs.pop(0)
        
        # Update FPS every second
        if current_time - self.last_fps_update_time >= self.fps_update_interval:
            self.fps = len(self.frame_times)  # Frames in the last second
            self.total_fps = len(self.frame_times_total)  # Total frames in the last second
            self.ibvs_fps = len(self.frame_times_ibvs)  # IBVS frames in the last second
            self.last_fps_update_time = current_time
        
        # Görüntülenen detections varsa IBVS'e gönderilmiş demektir
        if len(self.last_frame_detections) > 0:
            self.ibvs_processed_frames += 1
            # Add current time to IBVS frame times for IBVS FPS
            self.frame_times_ibvs.append(frame_time)
        
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
            self.logger.error(f"Dost/Düşman tespiti sırasında hata: {str(e)}")
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
        """Draw detection boxes on the frame with transparent overlay."""
        if not detections:
            return frame
            
        # Work on a copy of the frame
        output = frame.copy()
        
        # Create a mask for the enemy (dusman) detections (to create a dark transparent overlay)
        height, width = frame.shape[:2]
        mask = np.zeros((height, width), dtype=np.uint8)
        
        # Get the dusman class id
        dusman_class_id = -1
        dusman_names = ['dusman', 'düşman', 'enemy']  # Possible enemy class names
        
        # Check for possible enemy class names
        for enemy_name in dusman_names:
            if enemy_name in self.class_names:
                dusman_class_id = self.class_names.index(enemy_name)
                break
                
        if dusman_class_id == -1:
            # As fallback, try to use class with index 1 (assuming binary classification)
            if len(self.class_names) > 1:
                dusman_class_id = 1
        
        # Mark enemy regions in the mask
        for detection in detections:
            class_id = detection[5]
            
            if class_id == dusman_class_id:  # If this is a dusman (enemy)
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
        # Apply black color on the regions that are not inside enemy bounding boxes (where mask is 0)
        overlay[mask == 0] = [0, 0, 0]  # Black color
        
        # Blend the original frame with the overlay
        alpha = 0.3  # 30% of original image (70% opacity for black overlay)
        output = cv2.addWeighted(overlay, 1-alpha, frame, alpha, 0)
        
        # Now draw the detections
        for detection in detections:
            x, y, w, h = detection[:4]
            class_id = detection[5]
            track_id = detection[6] if len(detection) > 6 else -1
            
            # Make sure coordinates are valid
            x = max(0, int(x))
            y = max(0, int(y))
            w = int(w)
            h = int(h)
            
            # Ensure bounds are within frame
            if x + w > width:
                w = width - x
            if y + h > height:
                h = height - y
                
            if w <= 0 or h <= 0:
                continue
            
            # Get class name
            class_name = "unknown"
            if class_id < len(self.class_names):
                class_name = self.class_names[class_id]
            
            # Color scheme for friend/foe detection
            friend_foe_colors = {
                'dost': (0, 255, 0),     # Green for friends
                'dusman': (0, 0, 255),    # Red for enemies
                'düşman': (0, 0, 255),    # Red for enemies (Turkish)
                'enemy': (0, 0, 255)      # Red for enemies (English)
            }
            
            # Choose color based on class name
            color = (0, 255, 0)  # Default green
            if class_name in friend_foe_colors:
                color = friend_foe_colors[class_name]
            
            # Draw rectangle around detected object
            cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
            
            # Prepare label text with confidence
            conf = detection[4]
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
                    cv2.polylines(output, [points], False, color, 2)
        
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
        
        # Draw performance stats - mor renkte gösterelim
        stats_color = (255, 0, 255)  # Mor renk (magenta)
        
        cv2.putText(output, f"FPS: {self.fps}", 
                (width - 200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, stats_color, 2)
        
        cv2.putText(output, f"Total FPS: {self.total_fps}", 
                (width - 200, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, stats_color, 2)
        
        cv2.putText(output, f"IBVS FPS: {self.ibvs_fps}", 
                (width - 200, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, stats_color, 2)
        
        # Tespit sayısını da göster
        cv2.putText(output, f"Detections: {len(detections)}", 
                (width - 200, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, stats_color, 2)
        
        # Skip frame bilgisini göster
        cv2.putText(output, f"Skip Frame: {self.skip_frames}/{self.max_skip_frames+1}", 
                (width - 200, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, stats_color, 2)
        
        # Toplam frame sayılarını göster (birikimli)
        cv2.putText(output, f"Total Frames: {self.processed_frames}", 
                (10, height - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, stats_color, 1)
        
        cv2.putText(output, f"IBVS Frames: {self.ibvs_processed_frames}", 
                (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, stats_color, 1)
        
        return output 