#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modern Camera Application with PyQt5
------------------------------------
A full-screen camera application with animated sidebars,
logging functionality, and image capture capabilities.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from services.logger_service import LoggerService
import cv2
import numpy as np

# utils.config modülü içinde .env dosyası zaten yükleniyor
# böylece bu dosyayı import ettiğimizde çevresel değişkenler otomatik yüklenir
from utils.config import config

def main():
    # Initialize application
    app = QApplication(sys.argv)
    
    # Gerekli dizinlerin varlığını kontrol et ve oluştur
    # Bu merkezi bir fonksiyon sayesinde tüm dizinleri bir yerden yönetiyoruz
    config.ensure_dirs_exist()
    
    # Initialize logger service (singleton)
    logger = LoggerService()
    logger.info("Application started")
    
    # Create and show main window
    window = MainWindow()
    
    # Start application event loop
    sys.exit(app.exec_())

def detect_shapes_in_image(self, image, reference_shape=None, reference_color=None):
    """
    Detect shapes in an image.
    Identifies triangles, squares, and circles with red, green, or blue colors.
    """
    # Get image dimensions
    height, width = image.shape[:2]
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply adaptive threshold to handle different lighting conditions
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY_INV, 11, 2)
    
    # Apply morphological operations to clean up the image
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Process each contour to identify shapes
    shapes_found = []
    
    for contour in contours:
        # Filter out small contours
        area = cv2.contourArea(contour)
        if area < 100 or area > 10000:  # Minimum and maximum area threshold
            continue
        
        # Get the perimeter
        perimeter = cv2.arcLength(contour, True)
        
        # Approximate the contour
        epsilon = 0.04 * perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # Calculate circularity
        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
        
        # Determine shape type based on number of vertices and circularity
        shape_type = None
        
        if len(approx) == 3:
            shape_type = "triangle"
        elif len(approx) == 4:
            # Check if it's a square (aspect ratio close to 1)
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = float(w) / h
            if 0.8 <= aspect_ratio <= 1.2:
                shape_type = "square"
        elif circularity > 0.7:
            shape_type = "circle"
        
        # Skip if not one of our target shapes
        if not shape_type:
            continue
        
        # Get the center of the shape
        M = cv2.moments(contour)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            
            # Get the bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Create a mask for the shape
            shape_mask = np.zeros_like(gray)
            cv2.drawContours(shape_mask, [contour], 0, 255, -1)
            
            # Get the average color in BGR
            mean_color = cv2.mean(image, mask=shape_mask)[:3]
            
            # Identify the color name
            color_name = self.identify_simple_color(mean_color)
            
            # Store shape info
            shape_info = {
                'type': shape_type,
                'color': color_name,
                'center': (cx, cy),
                'top_left': (x, y),
                'width': w,
                'height': h,
                'circularity': circularity,
                'contour': contour
            }
            shapes_found.append(shape_info)
    
    return shapes_found

def identify_simple_color(self, bgr):
    """Identify the color name based on BGR values"""
    b, g, r = bgr
    
    # Find the dominant channel
    max_val = max(r, g, b)
    
    if max_val < 50:  # Very dark color
        return "black"
    
    if r > 200 and g > 200 and b > 200:
        return "white"
    
    # Check which channel is dominant with a significant margin
    if r > g*1.5 and r > b*1.5:
        return "red"
    elif g > r*1.5 and g > b*1.5:
        return "green"
    elif b > r*1.5 and b > g*1.5:
        return "blue"
    else:
        # If no clear dominant color, check which is highest
        if r >= g and r >= b:
            return "red"
        elif g >= r and g >= b:
            return "green"
        else:
            return "blue"

if __name__ == "__main__":
    main() 