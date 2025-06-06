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
from utils.config import config
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
        
        # Set default model path from config if not provided
        if model_path is None:
            self.model_path = config.get_balloon_model_path()
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
        self.max_track_history = 10
        
        # Track'lerin son görülme zamanını tutacak dictionary
        self.last_seen_time = {}
        self.track_timeout = 0.5  # Tracks will be removed after this many seconds of not being seen
        
        # Performans için ek ayarlar
        self.last_frame_detections = []
        
        # Kalman Filter Service
        self.kalman_service = KalmanFilterService()
        self.use_kalman = True  # Whether to use Kalman filtering
        self.show_kalman_debug = True  # Whether to show Kalman debug visualization
        
        # Frame and timing information
        self.frame_count = 0
        self.current_frame_id = None
        
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
        # Log
        self.logger.info("Balon dedektör servisi başlatıldı")
        return True
    
    def stop(self):
        """Stop the detection service."""
        self.is_initialized = False
        self.is_running = False
        # Track geçmişini temizle
        self.track_history.clear()
        self.last_seen_time.clear()
        # Log
        self.logger.info("Balon dedektör servisi durduruldu")
    
    def detect(self, frame):
        """
        Detect balloons in a frame and track them.
        Artık model inputu için frame'i 640x640'a resize ediyoruz ve bounding box'ları orijinal frame boyutuna scale ediyoruz.
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            List of detections, each containing [x, y, w, h, confidence, class_id, track_id]
        """
        if not self.is_initialized or not self.is_running:
            return []
        
        # Orijinal frame boyutunu sakla
        orig_h, orig_w = frame.shape[:2]
        # Model inputu için frame'i 640x640'a resize et
        input_size = 640
        resized_frame = cv2.resize(frame, (input_size, input_size))
        
        # Update processed frames count
        self.processed_frames += 1
        
        # Create a unique ID for this frame and mark it as received
        self.frame_count += 1
        self.current_frame_id = f"frame_{self.frame_count}_{time.time()}"
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
        
        if self.use_kalman:
            self.kalman_service.mark_frame_received(self.current_frame_id)
        
        # Zaman aşımına uğrayan track'leri temizle
        self._remove_stale_tracks(frame_time)
            
        try:
            if self.use_kalman:
                self.kalman_service.mark_processing_start(self.current_frame_id)
                
            # Performans için en iyi ayarlar
            half = self.use_gpu
            
            # YOLOv8 ile tespit yap, ByteTrack kullanarak
            results = self.model.track(
                resized_frame, 
                persist=True, 
                tracker="bytetrack.yaml", 
                verbose=False, 
                conf=0.25,  # Güven eşiği - düşük değer daha fazla tespit (ama yanlış pozitif olabilir)
                iou=0.45,   # IOU eşiği - kutuların çakışması için
                half=half,  # Half precision için
                imgsz=input_size,  # Resim boyutu
                max_det=20,  # Maksimum tespit sayısı
            )
            
            # Sonuçları işle (artık scale işlemi yapılacak)
            detections = self._process_results(results, (orig_h, orig_w), input_size, frame_time)
            
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
    
    def _process_results(self, results, orig_shape, input_size=640, frame_time=None):
        """Process YOLOv8 results to get detections and tracking info. Bounding box'ları orijinal frame boyutuna scale eder."""
        detections = []
        orig_h, orig_w = orig_shape[:2]
        scale_x = orig_w / input_size
        scale_y = orig_h / input_size
        current_time = time.time()
        frame_center = (orig_w // 2, orig_h // 2)
        current_track_ids = set()
        for result in results:
            if result.boxes is None or len(result.boxes) == 0:
                continue
            boxes = result.boxes
            track_ids = []
            if hasattr(boxes, 'id') and boxes.id is not None:
                track_ids = boxes.id.int().cpu().tolist()
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                # Scale bounding box to original frame size
                x1 = int(x1 * scale_x)
                y1 = int(y1 * scale_y)
                x2 = int(x2 * scale_x)
                y2 = int(y2 * scale_y)
                w = x2 - x1
                h = y2 - y1
                confidence = box.conf[0].cpu().numpy()
                class_id = int(box.cls[0].cpu().numpy())
                track_id = -1
                if i < len(track_ids):
                    track_id = track_ids[i]
                    current_track_ids.add(track_id)
                    self.last_seen_time[track_id] = current_time
                    track = self.track_history[track_id]
                    center_x = float(x1 + w / 2)
                    center_y = float(y1 + h / 2)
                    track.append((center_x, center_y))
                    if len(track) > self.max_track_history:
                        track.pop(0)
                    if self.use_kalman and track_id != -1:
                        self.kalman_service.update(track_id, (center_x, center_y), frame_time, frame_center)
                        self.kalman_service.predict(track_id, None, frame_center)
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
            # Nesne yoksa bile merkez noktasında başlayan bir tahmin çizimi için
            if len(detections) == 0:
                # "default_track" adında bir sahte track ID oluşturuyoruz
                dummy_track_id = "default_track"
                if dummy_track_id not in self.kalman_service.kalman_filters:
                    # Merkez noktasından başlayan bir kalman filter başlat
                    self.kalman_service.initialize_kalman(dummy_track_id, (center_x, center_y))
            
            # Standart debug görselleştirmesi
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
        
        # Toplam frame sayılarını göster (birikimli)
        cv2.putText(output, f"Total Frames: {self.processed_frames}", 
                (10, height - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, stats_color, 1)
        
        cv2.putText(output, f"IBVS Frames: {self.ibvs_processed_frames}", 
                (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, stats_color, 1)
        
        return output 