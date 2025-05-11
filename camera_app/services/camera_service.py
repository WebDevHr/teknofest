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
    
    def __init__(self, camera_id=None):
        super().__init__()
        self.logger = LoggerService()
        
        # Use camera_id from config if not specified
        self.camera_id = camera_id if camera_id is not None else config.camera_id
        self.capture = None
        self.timer = None
        self.is_running = False
        
        # FPS calculation variables
        self.prev_frame_time = 0
        self.curr_frame_time = 0
        self.fps = 0
        # Always show FPS
        self.show_fps = True
        
        # Daha kararlı FPS hesaplaması için
        self.frame_times = []
        self.max_frame_samples = 30  # Son 30 kareyi kullanarak ortalama hesapla
        
    def initialize(self):
        """Initialize the camera."""
        try:
            self.capture = cv2.VideoCapture(self.camera_id)
            
            if not self.capture.isOpened():
                error_msg = f"Kamera ID {self.camera_id} başlatılamadı"
                self.logger.error(error_msg)
                self.camera_error.emit(error_msg)
                return False
            
            self.logger.info(f"Kamera başarıyla başlatıldı (ID: {self.camera_id})")
            
            # Set initial resolution from config if available
            if hasattr(config, 'camera_width') and hasattr(config, 'camera_height'):
                self.set_resolution(config.camera_width, config.camera_height)
            
            return True
        except Exception as e:
            error_msg = f"Kamera başlatılırken hata: {str(e)}"
            self.logger.error(error_msg)
            self.camera_error.emit(error_msg)
            return False
    
    def set_resolution(self, width, height):
        """Set camera resolution."""
        if not self.capture or not self.capture.isOpened():
            return False
        
        try:
            # Try to set resolution
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Read actual values (may differ from requested)
            actual_width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            self.logger.info(f"Kamera çözünürlüğü ayarlandı: İstenen={width}x{height}, Gerçek={actual_width}x{actual_height}")
            return True
        except Exception as e:
            self.logger.error(f"Çözünürlük ayarlanırken hata: {str(e)}")
            return False
    
    def start(self, fps=None):
        """Start capturing frames at the specified FPS."""
        if not self.capture or not self.capture.isOpened():
            if not self.initialize():
                return False
        
        # Use FPS from config if not specified
        if fps is None:
            fps = config.camera_fps
        
        # Set resolution from config if available
        if hasattr(config, 'camera_width') and hasattr(config, 'camera_height'):
            self.set_resolution(config.camera_width, config.camera_height)
        else:
            # Use default resolution if not specified in config
            self.set_resolution(640, 480)
        
        # Set FPS
        self.capture.set(cv2.CAP_PROP_FPS, fps)
        
        # Set additional camera properties if available
        if hasattr(config, 'auto_exposure'):
            auto_exposure_value = 3 if config.auto_exposure else 1  # 3=auto, 1=manual
            self.capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, auto_exposure_value)
            
        if hasattr(config, 'auto_white_balance'):
            self.capture.set(cv2.CAP_PROP_AUTO_WB, 1 if config.auto_white_balance else 0)
        
        # Create and start timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._process_frame)
        interval = int(1000 / fps)  # Convert FPS to milliseconds
        self.timer.start(interval)
        
        self.is_running = True
        self.logger.info(f"Kamera başlatıldı (FPS: {fps})")
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
        """Calculate FPS."""
        self.curr_frame_time = time.time()
        
        # Add current frame time difference to the list
        if self.prev_frame_time > 0:
            time_diff = self.curr_frame_time - self.prev_frame_time
            self.frame_times.append(time_diff)
            
            # Keep only the most recent samples
            if len(self.frame_times) > self.max_frame_samples:
                self.frame_times.pop(0)
                
            # Calculate average FPS from samples
            avg_time = sum(self.frame_times) / len(self.frame_times)
            self.fps = 1.0 / avg_time if avg_time > 0 else 0
        
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
            
            # Check if we have an active detector service
            if hasattr(self, 'detector_service') and self.detector_service and self.detector_service.is_running:
                # Detect objects
                detections = self.detector_service.detect(frame)
                
                # Draw detections on frame
                frame = self.detector_service.draw_detections(frame, detections)
                
                # Apply IBVS visualization if pan-tilt service is available and tracking
                if hasattr(self, 'pan_tilt_service') and self.pan_tilt_service and self.pan_tilt_service.is_tracking:
                    # Find the target detection that's being tracked
                    target_detection = None
                    target_id = self.pan_tilt_service.target_id
                    
                    if target_id is not None:
                        # Look for the specific target ID
                        for detection in detections:
                            if len(detection) > 6 and detection[6] == target_id:
                                target_detection = detection
                                break
                    elif detections:
                        # Just use the first detection if no specific target
                        target_detection = detections[0]
                    
                    # Apply IBVS visualization
                    if target_detection is not None:
                        frame = self.pan_tilt_service.draw_tracking_visualization(frame, target_detection)
                
                # Apply PBVS visualization if PBVS service is available and tracking
                elif hasattr(self, 'pbvs_service') and self.pbvs_service and self.pbvs_service.is_tracking:
                    # Convert detections to format expected by PBVS service
                    pbvs_detections = []
                    for detection in detections:
                        # Format depends on the detector output format
                        # Typically: [x1, y1, x2, y2, conf, class_id, object_id]
                        if len(detection) >= 4:  # Ensure at least bbox coords
                            x1, y1, x2, y2 = detection[0:4]
                            conf = detection[4] if len(detection) > 4 else 0.0
                            class_id = detection[5] if len(detection) > 5 else 0
                            object_id = detection[6] if len(detection) > 6 else None
                            
                            # Calculate center and dimensions
                            center_x = (x1 + x2) / 2
                            center_y = (y1 + y2) / 2
                            width = x2 - x1
                            height = y2 - y1
                            
                            # Create detection dict
                            pbvs_detection = {
                                "center_x": center_x,
                                "center_y": center_y,
                                "width": width,
                                "height": height,
                                "confidence": conf,
                                "class_id": class_id,
                                "id": object_id
                            }
                            pbvs_detections.append(pbvs_detection)
                    
                    # Set detections in PBVS service
                    self.pbvs_service.set_detections(pbvs_detections)
                    
                    # Get the target detection based on target_id
                    target_detection = None
                    target_id = self.pbvs_service.target_id
                    
                    if target_id is not None:
                        # Find specific target ID
                        for detection in pbvs_detections:
                            if detection["id"] == target_id:
                                target_detection = detection
                                break
                    elif pbvs_detections:
                        # Just use the first detection if no specific target
                        target_detection = pbvs_detections[0]
                    
                    # Apply PBVS visualization
                    frame = self.pbvs_service.draw_tracking_visualization(frame, target_detection)
            
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
        """Toggle FPS display. (Kept for backwards compatibility)"""
        # Always return True since FPS is always shown now
        return True
    
    def get_frame_dimensions(self):
        """Get the dimensions of the current frame.
        
        Returns:
            tuple: (width, height) of the current frame, or default values if camera not available.
        """
        if not self.capture or not self.capture.isOpened():
            # Return config values if available, otherwise default values
            if hasattr(config, 'camera_width') and hasattr(config, 'camera_height'):
                return (config.camera_width, config.camera_height)
            return (640, 480)  # Return default values if camera not available
            
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (width, height)
    
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
    
    def set_detector_service(self, detector_service):
        """Set the current active detector service."""
        # Remove any previous detector service
        if hasattr(self, 'detector_service') and self.detector_service:
            self.detector_service.stop()
            
        # Set the new detector service
        self.detector_service = detector_service
        self.logger.info(f"Aktif dedektör değiştirildi: {detector_service.__class__.__name__}")
    
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
            # Check save format from config
            if hasattr(config, 'save_format'):
                ext = os.path.splitext(filename)[1].lower()
                if config.save_format == "JPEG" and ext != ".jpg" and ext != ".jpeg":
                    filename = os.path.splitext(filename)[0] + ".jpg"
                elif config.save_format == "PNG" and ext != ".png":
                    filename = os.path.splitext(filename)[0] + ".png"
                elif config.save_format == "BMP" and ext != ".bmp":
                    filename = os.path.splitext(filename)[0] + ".bmp"
            
            # Save the image
            cv2.imwrite(filename, frame)
            self.logger.info(f"Mevcut kare {filename} olarak kaydedildi")
            return True
        else:
            self.logger.error("Mevcut kare kaydedilemedi")
            return False
    
    def set_pan_tilt_service(self, pan_tilt_service):
        """Set the pan-tilt service for camera movement and IBVS tracking."""
        self.pan_tilt_service = pan_tilt_service
        
        # Update the frame center in the pan-tilt service
        width, height = self.get_frame_dimensions()
        pan_tilt_service.set_frame_center(width, height)
        
        self.logger.info(f"Pan-tilt service set in Camera Service")
    
    def set_pbvs_service(self, pbvs_service):
        """Set the PBVS service for camera movement and position-based tracking."""
        self.pbvs_service = pbvs_service
        
        # Update the frame center in the PBVS service
        width, height = self.get_frame_dimensions()
        pbvs_service.set_frame_center(width, height)
        
        self.logger.info(f"PBVS service set in Camera Service")
    
    def get_available_resolutions(self):
        """Get a list of common resolutions that might be supported by the camera.
        
        Returns:
            list: List of resolution strings in format "widthxheight"
        """
        # Common camera resolutions
        resolutions = [
            "320x240",
            "640x480",
            "800x600",
            "1024x768",
            "1280x720",
            "1920x1080",
            "2560x1440"
        ]
        return resolutions 