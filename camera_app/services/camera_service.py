#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Camera Service
-------------
Service for handling camera operations.
"""

import cv2
import os
import time
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QImage
from services.logger_service import LoggerService
from utils.config import config

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
        
        # FPS calculation variables
        self.prev_frame_time = 0
        self.curr_frame_time = 0
        self.fps = 0
        self.show_fps = True
        
    def initialize(self):
        """Initialize the camera."""
        self.capture = cv2.VideoCapture(self.camera_id)
        
        if not self.capture.isOpened():
            error_msg = f"Kamera ID {self.camera_id} başlatılamadı"
            self.logger.error(error_msg)
            self.camera_error.emit(error_msg)
            return False
        
        self.logger.info(f"Kamera başarıyla başlatıldı (ID: {self.camera_id})")
        return True
    
    def start(self, fps=30):
        """Start capturing frames at the specified FPS."""
        if not self.capture or not self.capture.isOpened():
            if not self.initialize():
                return False
        
        # Kamerayı daha düşük çözünürlüğe ayarla (performans için)
        # self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        # self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Create and start timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._process_frame)
        interval = int(1000 / fps)  # Convert FPS to milliseconds
        self.timer.start(interval)
        
        self.is_running = True
        self.logger.info(f"Kamera {fps} FPS hızında başlatıldı")
        return True
    
    def stop(self):
        """Stop capturing frames."""
        if self.timer:
            self.timer.stop()
            
        self.is_running = False
        self.logger.info("Kamera durduruldu")
    
    def release(self):
        """Release camera resources."""
        self.stop()
        
        if self.capture:
            self.capture.release()
            self.capture = None
            self.logger.info("Kamera kaynakları serbest bırakıldı")
    
    def _calculate_fps(self):
        """Calculate the current FPS."""
        self.curr_frame_time = time.time()
        # Calculate FPS only if we have a previous frame time
        if self.prev_frame_time > 0:
            # Calculate time difference between current and previous frame
            time_diff = self.curr_frame_time - self.prev_frame_time
            # Calculate FPS
            if time_diff > 0:
                self.fps = 1 / time_diff
        # Update previous frame time
        self.prev_frame_time = self.curr_frame_time
    
    def _draw_fps(self, frame):
        """Draw FPS counter on the frame."""
        # This function no longer displays FPS on the frame
        # FPS is now displayed on the main window instead
        # We keep this method for compatibility
        return frame
    
    def _process_frame(self):
        """Process a frame from the camera."""
        if not self.capture or not self.capture.isOpened():
            self.camera_error.emit("Kamera mevcut değil")
            self.stop()
            return
            
        ret, frame = self.capture.read()
        if ret:
            # Calculate FPS
            self._calculate_fps()
            
            # Kare sayacını artır
            if not hasattr(self, 'frame_count'):
                self.frame_count = 0
            self.frame_count += 1
            
            # Performans için resmi küçültebiliriz (isteğe bağlı)
            # frame = cv2.resize(frame, (640, 480))
            
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
            
            # Draw FPS counter (after all processing)
            frame = self._draw_fps(frame)
            
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
            self.camera_error.emit("Kare yakalama hatası")
    
    def toggle_fps_display(self):
        """Toggle the display of FPS counter."""
        self.show_fps = not self.show_fps
        self.logger.info(f"FPS gösterimi {('etkinleştirildi' if self.show_fps else 'devre dışı bırakıldı')}")
        return self.show_fps
    
    def capture_image(self):
        """Capture and save the current frame."""
        if not self.capture or not self.capture.isOpened():
            self.logger.error("Kamera mevcut değil")
            return None
            
        # Get the captures directory from config
        directory = config.captures_dir
            
        # Create directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(directory, f"capture_{timestamp}.png")
        
        # Capture frame
        ret, frame = self.capture.read()
        if ret:
            # Save the image
            cv2.imwrite(filename, frame)
            self.logger.info(f"Görüntü yakalandı ve {filename} olarak kaydedildi")
            return filename
        else:
            self.logger.error("Görüntü kaydedilemedi")
            return None
    
    def set_yolo_service(self, yolo_service):
        """Set the YOLO service for object detection."""
        self.yolo_service = yolo_service
        self.logger.info("YOLO servisi kameraya bağlandı")
    
    def set_shape_detection_service(self, shape_detection_service):
        """Set the shape detection service."""
        self.shape_detection_service = shape_detection_service
        self.logger.info("Şekil algılama servisi kameraya bağlandı")
    
    def set_roboflow_service(self, roboflow_service):
        """Set the Roboflow service for object detection."""
        self.roboflow_service = roboflow_service
        self.logger.info("Roboflow servisi kameraya bağlandı")
    
    def save_current_frame(self, filename):
        """Save the current frame to the specified file."""
        if not self.capture or not self.capture.isOpened():
            self.logger.error("Kamera mevcut değil")
            return False
            
        # Ensure directory exists
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        # Capture frame
        ret, frame = self.capture.read()
        if ret:
            # Save the image
            cv2.imwrite(filename, frame)
            self.logger.info(f"Mevcut kare {filename} olarak kaydedildi")
            return True
        else:
            self.logger.error("Mevcut kare kaydedilemedi")
            return False 