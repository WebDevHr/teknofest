#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Shape Detection Service
---------------------
Service for detecting shapes in camera frames.
"""

import cv2
import numpy as np
import os
import time
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService

class ShapeDetectionService(QObject):
    """
    Service for detecting shapes in camera frames.
    """
    # Signals
    detection_ready = pyqtSignal(object, list)  # frame, shapes
    
    def __init__(self):
        super().__init__()
        self.logger = LoggerService()
        self.is_running = False
        self.reference_shape = None
        self.reference_color = None
        self.output_dir = "shape_detection"
        self.csv_file = None
        self.last_snapshot_time = 0
        self.snapshot_interval = 5  # seconds
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.info(f"Created output directory: {self.output_dir}")
    
    def start(self):
        """Start the shape detection service."""
        self.is_running = True
        self.logger.info("Shape detection started")
        return True
    
    def stop(self):
        """Stop the shape detection service."""
        self.is_running = False
        self.logger.info("Shape detection stopped")
    
    def detect(self, frame, frame_count=0):
        """
        Detect shapes in a frame.
        
        Args:
            frame: OpenCV image (BGR format)
            frame_count: Current frame count
            
        Returns:
            List of detected shapes
        """
        if not self.is_running:
            return []
            
        try:
            # Detect shapes in the frame
            shapes = self.detect_shapes_in_image(frame)
            
            # Process the frame for display
            display_frame = frame.copy()
            
            # Draw all shapes
            for shape in shapes:
                # Get the center coordinates
                cx, cy = shape['center']
                
                # Draw the shape on the display frame
                border_color = (0, 0, 255)  # Default: red
                if shape['type'] == "triangle":
                    border_color = (0, 0, 255)  # Red for triangles
                elif shape['type'] == "square":
                    border_color = (0, 255, 0)  # Green for squares
                elif shape['type'] == "circle":
                    border_color = (255, 0, 0)  # Blue for circles
                    
                cv2.drawContours(display_frame, [shape['contour']], 0, border_color, 2)
                
                # Add text label with shape and color
                label = f"{shape['color']} {shape['type']}"
                cv2.putText(display_frame, label, (cx - 30, cy), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Store the processed frame for display
            self.processed_frame = display_frame
            
            # Save coordinates to CSV if needed
            if hasattr(self, 'csv_path') and shapes:
                with open(self.csv_path, 'a') as f:
                    for shape in shapes:
                        cx, cy = shape['center']
                        f.write(f"{frame_count},{shape['type']},{shape['color']},{cx},{cy},{time.time()}\n")
            
            return shapes
            
        except Exception as e:
            self.logger.error(f"Error during shape detection: {str(e)}")
            return []
    
    def detect_shapes_in_image(self, image):
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
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Process each contour to identify shapes
        shapes_found = []
        
        for contour in contours:
            # Filter out small contours
            area = cv2.contourArea(contour)
            if area < 500 or area > 50000:  # Adjust area thresholds
                continue
            
            # Get the perimeter
            perimeter = cv2.arcLength(contour, True)
            
            # Approximate the contour
            epsilon = 0.04 * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Calculate circularity
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            
            # Determine shape type based on number of vertices and circularity
            shape_type = "unknown"
            
            if len(approx) == 3:
                shape_type = "triangle"
            elif len(approx) == 4:
                # Check if it's a square (aspect ratio close to 1)
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = float(w) / h
                if 0.8 <= aspect_ratio <= 1.2:
                    shape_type = "square"
                else:
                    shape_type = "rectangle"
            elif circularity > 0.7:
                shape_type = "circle"
            
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
        
        # Check for whitish/grayish color (all channels high and close to each other)
        if r > 150 and g > 150 and b > 150 and abs(r-g) < 30 and abs(r-b) < 30 and abs(g-b) < 30:
            return "white"
        
        # Check which channel is dominant with a significant margin
        if r > g*1.3 and r > b*1.3:
            return "red"
        elif g > r*1.3 and g > b*1.3:
            return "green"
        elif b > r*1.3 and b > g*1.3:
            return "blue"
        else:
            # If no clear dominant color, check which is highest
            if r >= g and r >= b:
                return "red"
            elif g >= r and g >= b:
                return "green"
            else:
                return "blue" 