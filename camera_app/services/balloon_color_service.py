#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Balloon Color Detector Service
----------------------------
HSV renk segmentasyonu ve thresholding ile balon tespiti servisi.
"""

import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService

class BalloonColorService(QObject):
    """
    HSV renk segmentasyonu ile balon tespiti servisi.
    """
    detection_ready = pyqtSignal(object, list)  # frame, detections

    def __init__(self):
        super().__init__()
        self.logger = LoggerService()
        self.is_initialized = True
        self.is_running = False

    def initialize(self):
        self.is_initialized = True
        self.logger.info("Renk Segmentasyon Balon Tespit Servisi başlatıldı")
        return True

    def start(self):
        self.is_running = True
        self.logger.info("Renk Segmentasyon Balon Tespit Servisi çalışıyor")
        return True

    def stop(self):
        self.is_running = False
        self.logger.info("Renk Segmentasyon Balon Tespit Servisi durduruldu")

    def detect(self, frame):
        if not self.is_running:
            return []

        detections = []
        output = frame.copy()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Renk aralıkları (HSV)
        color_ranges = [
            # Kırmızı (iki aralık, HSV wrap-around)
            (np.array([0, 90, 80]), np.array([10, 255, 255])),   # Alt kırmızı
            (np.array([160, 90, 80]), np.array([180, 255, 255])), # Üst kırmızı
            # Yeşil
            (np.array([35, 80, 80]), np.array([85, 255, 255])),
            # Mavi
            (np.array([90, 80, 80]), np.array([130, 255, 255]))
        ]
        # class_id: 0=kırmızı, 1=yeşil, 2=mavi
        color_ids = [0, 0, 1, 2]

        for idx, (lower, upper) in enumerate(color_ranges):
            mask = cv2.inRange(hsv, lower, upper)
            # Gürültü azaltma
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
            mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, np.ones((7,7), np.uint8))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 150:
                    continue
                (x, y, w, h) = cv2.boundingRect(cnt)
                aspect_ratio = float(w) / h if h > 0 else 0
                if 0.5 < aspect_ratio < 1.5:
                    confidence = 0.8
                    class_id = color_ids[idx]
                    track_id = -1
                    detections.append([int(x), int(y), int(w), int(h), confidence, class_id, track_id])
                    # Debug çizim
                    color = [(0,0,255), (0,255,0), (255,0,0)][class_id]
                    cv2.rectangle(output, (x, y), (x+w, y+h), color, 2)

        self.detection_ready.emit(output, detections)
        return detections

    def draw_detections(self, frame, detections):
        output = frame.copy()
        for det in detections:
            x, y, w, h, conf, class_id, track_id = det
            color = [(0,0,255), (0,255,0), (255,0,0)][class_id]
            cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
            label = f"Balon: {['Kırmızı','Yeşil','Mavi'][class_id]}"
            cv2.putText(output, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return output 