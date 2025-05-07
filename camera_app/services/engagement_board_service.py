#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Engagement Board Service
----------------------
Service for detecting engagement board and recognizing characters using YOLO and OCR.
For 3. Aşama - Angajman Tahtası Okuması
"""

import cv2
import numpy as np
import os
import torch
import easyocr
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from services.logger_service import LoggerService
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont

class EngagementBoardService(QObject):
    """
    Service for handling engagement board detection using YOLO model and OCR.
    Detects the character (A or B) on the board and engagement shapes.
    """
    # Signals
    detection_ready = pyqtSignal(object, list, str, str)  # frame, detections, ocr_text, class_turkish
    detection_completed = pyqtSignal(str)  # Tespit edilen sınıf adı (red-square, green-circle vb.)
    
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
        self.ocr_reader = None
        self.is_initialized = False
        self.is_running = False
        self.ocr_text = ""
        self.class_name = ""
        self.detection_done = False
        
        # Turkish translation mapping for shapes
        self.turkish_classes = {
            "red-circle": "Kırmızı Daire",
            "red-square": "Kırmızı Kare",
            "red-triangle": "Kırmızı Üçgen",
            "blue-circle": "Mavi Daire",
            "blue-square": "Mavi Kare",
            "blue-triangle": "Mavi Üçgen",
            "green-circle": "Yeşil Daire",
            "green-square": "Yeşil Kare",
            "green-triangle": "Yeşil Üçgen",
            "unknown": "Bilinmeyen"
        }
        
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
        
    def initialize(self, model_path=None):
        """Initialize the YOLO model and OCR reader."""
        if model_path:
            self.model_path = model_path
            
        if not self.model_path or not os.path.exists(self.model_path):
            self.logger.error(f"Angajman tahtası dedektör model dosyası bulunamadı: {self.model_path}")
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
            
            # Initialize EasyOCR reader
            self.ocr_reader = easyocr.Reader(['en'], gpu=self.use_gpu)
            
            # Log success
            self.logger.info(f"Angajman tahtası dedektör modeli yüklendi: {self.model_path}, Cihaz: {device}")
            self.logger.info("EasyOCR okuyucu başlatıldı")
            self.is_initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Angajman tahtası dedektör başlatılamadı: {str(e)}")
            return False
    
    def start(self):
        """Start the detection service."""
        if not self.is_initialized:
            self.logger.error("Angajman tahtası dedektör modeli initialize edilmedi")
            return False
            
        self.is_running = True
        self.logger.info("Angajman tahtası dedektör servisi başlatıldı")
        return True
    
    def stop(self):
        """Stop the detection service."""
        self.is_running = False
        self.logger.info("Angajman tahtası dedektör servisi durduruldu")
    
    def detect(self, frame):
        """
        Detect shapes and OCR in a single frame.
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            List of detections, each containing [x, y, w, h, confidence, class_id]
        """
        if not self.is_initialized or not self.is_running:
            return []
        
        # If we already have a detection, just return it
        if self.detection_done:
            return []
            
        try:
            # Perform YOLO detection
            half = self.use_gpu  # GPU kullanıyorsa half precision kullan
            img_size = 640  # Standard size for detection
            
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
            
            # Perform OCR
            self.ocr_text = self._perform_ocr(frame)
            
            # Process YOLO results
            detections = self._process_results(results, frame.shape)
            
            # Check if we have both character and shape detection
            if self.ocr_text and len(detections) > 0 and not hasattr(self, 'detection_timer'):
                # İlk tespit yapıldığında
                self.logger.info(f"Tespit yapıldı: Karakter: {self.ocr_text}, Şekil: {self.class_name}")
                self.logger.info("3 saniye boyunca sonuç gösteriliyor...")
                
                # 3 saniye sonra servis değişimi için timer oluştur
                self.detection_timer = QTimer()
                self.detection_timer.setSingleShot(True)
                self.detection_timer.timeout.connect(self._complete_detection)
                self.detection_timer.start(3000)  # 3 saniye (3000 ms)
            
            # Emit signal with results
            turkish_class_name = self.turkish_classes.get(self.class_name, "Bilinmeyen")
            self.detection_ready.emit(frame, detections, self.ocr_text, turkish_class_name)
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Angajman tahtası tespiti sırasında hata: {str(e)}")
            return []
    
    def _perform_ocr(self, frame):
        """Perform OCR on the frame to detect A or B character."""
        try:
            # Pre-process the image for better OCR
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold to make the text more visible
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
            
            # Perform OCR
            result = self.ocr_reader.readtext(thresh)
            
            # Filter results for A or B
            detected_text = ""
            for detection in result:
                text = detection[1].upper().strip()
                if text == 'A' or text == 'B':
                    detected_text = text
                    confidence = detection[2]
                    self.logger.info(f"OCR tespit edildi: '{text}' (güven: {confidence:.2f})")
                    break
            
            return detected_text
        except Exception as e:
            self.logger.error(f"OCR sırasında hata: {str(e)}")
            return ""
    
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
                
                # Get class name
                if class_id < len(self.class_names):
                    self.class_name = self.class_names[class_id]
                else:
                    self.class_name = "unknown"
                
                # Tespit listesine ekle [x, y, w, h, confidence, class_id]
                detections.append([int(x1), int(y1), int(w), int(h), float(confidence), class_id])
        
        return detections
    
    def cv2_put_turkish_text(self, img, text, position, font_size=32, text_color=(255, 255, 255)):
        """OpenCV ile Türkçe karakterleri düzgün göstermek için PIL kullanarak metin ekler."""
        # OpenCV görüntüsünü RGB'ye dönüştür (PIL için)
        rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        
        # Font yolunu belirle (Windows'ta varsayılan font kullan)
        try:
            # Windows sisteminde Arial.ttf'yi bul
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            # Arial bulunamazsa, varsayılan bir font kullan
            font = ImageFont.load_default()
        
        # PIL görüntüsüne metin ekle
        draw = ImageDraw.Draw(pil_image)
        draw.text(position, text, font=font, fill=text_color)
        
        # PIL görüntüsünü OpenCV formatına geri dönüştür
        result = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        return result
    
    def draw_detections(self, frame, detections):
        """Draw detection boxes and OCR result on the frame."""
        if not detections and not self.ocr_text:
            return frame
            
        # Work on a copy of the frame
        output = frame.copy()
        
        # Draw each detection if any
        if detections:
            # Colors for engagement shapes/colors
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
            
            for detection in detections:
                x, y, w, h, conf, class_id = detection[:6]
                
                # Get class name
                class_name = "unknown"
                if class_id < len(self.class_names):
                    class_name = self.class_names[class_id]
                
                # Choose color based on class name
                color = (128, 128, 128)  # Default gray
                for key, color_value in engagement_colors.items():
                    if class_name == key:
                        color = color_value
                        break
                
                # Draw rectangle
                cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
                
                # Prepare text
                text = f"{class_name}: {conf:.2f}"
                
                # Draw text background
                text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(output, (x, y - 20), (x + text_size[0], y), color, -1)
                
                # Draw text
                cv2.putText(output, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # Create a semi-transparent overlay at the bottom of the image for result display
        if self.detection_done and (self.ocr_text or self.class_name):
            # Create large background
            h, w = output.shape[:2]
            overlay = output.copy()
            
            # Get Turkish name of the class
            turkish_class = self.turkish_classes.get(self.class_name, "Bilinmeyen")
            
            # Draw a semi-transparent background
            cv2.rectangle(overlay, (0, h-150), (w, h), (0, 0, 0), -1)
            alpha = 0.7
            output = cv2.addWeighted(overlay, alpha, output, 1-alpha, 0)
            
            # Draw character and class information using PIL for Turkish characters
            if self.ocr_text:
                char_text = f"Karakter: {self.ocr_text}"
                # Calculate position for center alignment
                font_size = 40
                x = w // 2 - 150  # Yaklaşık merkezle
                output = self.cv2_put_turkish_text(output, char_text, (x, h-100), font_size)
            
            if turkish_class != "Bilinmeyen":
                class_text = f"Şekil: {turkish_class}"
                # Calculate position for center alignment
                x = w // 2 - 150  # Yaklaşık merkezle
                output = self.cv2_put_turkish_text(output, class_text, (x, h-50), font_size)
            
        # If not in detection_done state but have a character or class, show at top of frame
        elif self.ocr_text or self.class_name:
            # Draw OCR result if available
            if self.ocr_text:
                # Prepare text with larger font
                text = f"Karakter: {self.ocr_text}"
                
                # Draw text at the top center of the frame
                x = output.shape[1] // 2 - 100  # Approximate center
                output = self.cv2_put_turkish_text(output, text, (x, 50), 32)
        
        return output 
    
    def _complete_detection(self):
        """3 saniye sonra çağrılır ve detection_completed sinyalini gönderir."""
        self.detection_done = True
        self.logger.info(f"Tespit tamamlandı: Karakter: {self.ocr_text}, Şekil: {self.class_name}")
        self.logger.info(f"Angajman Mode'a geçiliyor, hedef sınıf: {self.class_name}")
        
        # Tespit edilen sınıfı ilet
        self.detection_completed.emit(self.class_name) 