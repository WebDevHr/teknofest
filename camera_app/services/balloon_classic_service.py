#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Balloon Classic Detector Service
-------------------------------
Klasik yöntemlerle balon tespiti servisi.
"""

import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService

class BalloonClassicService(QObject):
    """
    Klasik yöntemlerle balon tespiti servisi.
    """
    detection_ready = pyqtSignal(object, list)  # frame, detections

    def __init__(self):
        super().__init__()
        self.logger = LoggerService()
        self.is_initialized = True
        self.is_running = False

    def initialize(self):
        self.is_initialized = True
        self.logger.info("Klasik Balon Tespit Servisi başlatıldı")
        return True

    def start(self):
        self.is_running = True
        self.logger.info("Klasik Balon Tespit Servisi çalışıyor")
        return True

    def stop(self):
        self.is_running = False
        self.logger.info("Klasik Balon Tespit Servisi durduruldu")

    def detect(self, frame):
        """
        Canny, kontur ve Hough Circle ile balon tespiti uygular.
        Dönüş: [x, y, w, h, confidence, class_id, track_id]
        """
        if not self.is_running:
            return []

        detections = []
        output = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)

        # 1. Canny Edge
        edges = cv2.Canny(blurred, 50, 150)

        # 2. Kontur bulma
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 200:  # Çok küçük konturları atla
                continue
            (x, y, w, h) = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h if h > 0 else 0
            if 0.7 < aspect_ratio < 1.3:  # Daireye yakınlık
                # 3. Hough Circle ile doğrulama (isteğe bağlı)
                # (Alternatif: minEnclosingCircle ile de kontrol edilebilir)
                ((cx, cy), radius) = cv2.minEnclosingCircle(cnt)
                if 10 < radius < 50:  # Boyut filtresi (10-50 px arası)
                    confidence = 0.7  # Klasik yöntem, sabit confidence
                    class_id = 0  # Balon
                    track_id = -1  # Takip yok
                    detections.append([int(x), int(y), int(w), int(h), confidence, class_id, track_id])

        self.detection_ready.emit(output, detections)
        return detections

    def draw_detections(self, frame, detections):
        output = frame.copy()
        for det in detections:
            x, y, w, h, conf, class_id, track_id = det
            cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 255), 2)
            label = f"Balon: {conf:.2f}"
            cv2.putText(output, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        return output 