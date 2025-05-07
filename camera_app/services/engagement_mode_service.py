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
        
        # Sadece belirli bir sınıfı tespit etme ayarı
        self.target_class = None  # Varsayılan olarak tüm sınıfları tespit et
        
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
            
            # Mevcut sınıf isimlerini logla
            class_names_str = ', '.join([f"{i}:{name}" for i, name in self.class_names.items()])
            self.logger.info(f"Algılanabilen sınıflar: {class_names_str}")
            
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
    
    def set_target_class(self, class_name):
        """Sadece belirtilen sınıfı tespit etmek için ayarla."""
        # Mevcut sınıf isimlerini kontrol et
        self.logger.info(f"Mevcut sınıflar: {list(self.class_names.values())}")
        
        # class_names değerleri içinde kontrol et
        class_exists = class_name in self.class_names.values()
        
        if class_exists:
            self.target_class = class_name
            self.logger.info(f"Hedef sınıf '{class_name}' olarak ayarlandı")
            return True
        else:
            # YOLO modelinin kullandığı sınıf isimlerine uyum sağlamak için alternatif isimler kontrolü
            # Örneğin "red-square" yerine modelde "kırmızı kare" geçiyorsa
            alternative_names = {
                "red-square": ["kirmizi-kare", "kirmizi_kare", "red_square", "red square"],
                "red-circle": ["kirmizi-daire", "kirmizi_daire", "red_circle", "red circle"],
                "red-triangle": ["kirmizi-ucgen", "kirmizi_ucgen", "red_triangle", "red triangle"],
                "blue-square": ["mavi-kare", "mavi_kare", "blue_square", "blue square"],
                "blue-circle": ["mavi-daire", "mavi_daire", "blue_circle", "blue circle"],
                "blue-triangle": ["mavi-ucgen", "mavi_ucgen", "blue_triangle", "blue triangle"],
                "green-square": ["yesil-kare", "yesil_kare", "green_square", "green square"],
                "green-circle": ["yesil-daire", "yesil_daire", "green_circle", "green circle"],
                "green-triangle": ["yesil-ucgen", "yesil_ucgen", "green_triangle", "green triangle"]
            }
            
            # Alternatif isimlerle eşleşme kontrol et
            for target_class, alternatives in alternative_names.items():
                if class_name == target_class:
                    # Orijinal ad doğru ama model içinde farklı bir formatta olabilir
                    for i, name in self.class_names.items():
                        if name in alternatives or any(alt in name.lower() for alt in alternatives):
                            self.target_class = name
                            self.logger.info(f"Hedef sınıf '{class_name}' yerine model içindeki '{name}' olarak ayarlandı")
                            return True
            
            # Eğer buraya kadar geldiyse, sınıf bulunamadı
            self.logger.warning(f"Geçersiz sınıf adı: {class_name}. Sınıf modelde bulunamadı.")
            # Varsayılan olarak ilk sınıfı kullan (hata durumunda)
            self.target_class = list(self.class_names.values())[0] if self.class_names else None
            self.logger.info(f"Varsayılan hedef sınıf '{self.target_class}' olarak ayarlandı")
            return False
    
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
                
                # Sınıf adını al
                class_name = "unknown"
                if class_id in self.class_names:
                    class_name = self.class_names[class_id]
                
                # Tüm sınıfları tespit et, ancak hedef sınıf olup olmadığını detections içinde belirt
                is_target = False
                if self.target_class is not None:
                    if class_name == self.target_class:
                        is_target = True
                
                # Tespit listesine ekle [x, y, w, h, confidence, class_id, is_target]
                detections.append([int(x1), int(y1), int(w), int(h), float(confidence), class_id, is_target])
        
        return detections
    
    def draw_detections(self, frame, detections):
        """Draw detection boxes on the frame with transparent overlay."""
        if not detections:
            return frame
            
        # Work on a copy of the frame
        output = frame.copy()
        
        # Create a mask for target shape detections
        height, width = frame.shape[:2]
        target_mask = np.zeros((height, width), dtype=np.uint8)
        
        # Mark only target regions in the mask (sadece hedef sınıf için mask oluştur)
        for detection in detections:
            if len(detection) >= 7:  # is_target değerini içeren detections
                x, y, w, h, conf, class_id, is_target = detection[:7]
                
                if is_target:  # Sadece hedef nesneler için mask uygula
                    # Make sure coordinates are valid
                    x = max(0, int(x))
                    y = max(0, int(y))
                    x2 = min(width, x + int(w))
                    y2 = min(height, y + int(h))
                    
                    # Fill the detected region in the mask
                    target_mask[y:y2, x:x2] = 255
        
        # Create a semi-transparent black overlay
        overlay = frame.copy()
        # Apply black color on the regions that are not inside target detection bounding boxes
        overlay[target_mask == 0] = [0, 0, 0]  # Black color
        
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
            if len(detection) >= 7:  # is_target değerini içeren detections
                x, y, w, h, conf, class_id, is_target = detection[:7]
            else:
                x, y, w, h, conf, class_id = detection[:6]
                is_target = False
            
            # Get class name
            class_name = "unknown"
            if class_id < len(self.class_names):
                class_name = self.class_names[class_id]
            
            # Choose color based on class name
            color = (0, 255, 0)  # Default green
            if class_name in engagement_colors:
                color = engagement_colors[class_name]
            
            # Hedef sınıfı daha belirgin göster
            thickness = 3 if is_target else 1
            
            # Draw rectangle around detected object
            cv2.rectangle(output, (x, y), (x + w, y + h), color, thickness)
            
            # Prepare label text with confidence
            label = f"{class_name}: {conf:.2f}"
            
            # Hedef sınıf için daha belirgin etiket
            if is_target:
                # Draw label background
                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(output, (x, y - 25), (x + text_size[0], y), color, -1)
                
                # Draw label text
                cv2.putText(output, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            else:
                # Hedef olmayan sınıflar için daha küçük ve şeffaf etiket
                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                
                # Şeffaf arka plan ile birleştirme
                overlay_text = output.copy()
                cv2.rectangle(overlay_text, (x, y - 20), (x + text_size[0], y), color, -1)
                output = cv2.addWeighted(overlay_text, 0.5, output, 0.5, 0)
                
                # Daha küçük yazı
                cv2.putText(output, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return output 