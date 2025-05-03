#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Shape Detection Service
---------------------
Service for detecting white areas in camera frames.
"""

import cv2
import numpy as np
import os
import time
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService

class ShapeDetectionService(QObject):
    """
    Service for detecting white areas in camera frames.
    """
    # Signals
    detection_ready = pyqtSignal(object, list)  # frame, white_regions
    
    def __init__(self):
        super().__init__()
        self.logger = LoggerService()
        self.is_running = False
        
        # FPS calculation variables
        self.prev_frame_time = 0
        self.curr_frame_time = 0
        self.fps = 0
        
    def start(self):
        """Start the white area detection service."""
        self.is_running = True
        self.logger.info("Beyaz alan algılama başlatıldı")
        return True
    
    def stop(self):
        """Stop the white area detection service."""
        self.is_running = False
        self.logger.info("Beyaz alan algılama durduruldu")
    
    def detect(self, frame, frame_count=0):
        """
        Detect white areas in a frame.
        
        Args:
            frame: OpenCV image (BGR format)
            frame_count: Current frame count
            
        Returns:
            List of detected white regions
        """
        if not self.is_running:
            return []
            
        try:
            # Calculate FPS
            self.curr_frame_time = time.time()
            if self.prev_frame_time != 0:
                self.fps = 1 / (self.curr_frame_time - self.prev_frame_time)
            self.prev_frame_time = self.curr_frame_time
            
            # Detect white areas in the frame
            white_regions = self.detect_white_balloons(frame)
            
            return white_regions
            
        except Exception as e:
            self.logger.error(f"Error during white area detection: {str(e)}")
            return []
    
    def detect_white_balloons(self, image):
        """
        Detect white balloons in an image using K-means clustering to handle
        different shades of white including shadowy parts.
        
        Args:
            image: OpenCV image (BGR format)
            
        Returns:
            List of contours representing circular white areas (balloons)
        """
        # Create a copy for drawing results
        display_frame = image.copy()
        
        # Create a black frame for the output
        output_frame = np.zeros_like(image)
        
        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(image, 9, 75, 75)
        
        # Convert to LAB color space which is better for color clustering
        lab_image = cv2.cvtColor(filtered, cv2.COLOR_BGR2LAB)
        
        # Reshape the image for K-means
        pixels = lab_image.reshape((-1, 3))
        pixels = np.float32(pixels)
        
        # Define criteria for K-means
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        k = 5  # Number of clusters (adjust as needed)
        
        # Apply K-means clustering
        _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # Convert back to 8-bit values
        centers = np.uint8(centers)
        
        # Reshape labels to the original image shape
        labels_reshaped = labels.reshape(image.shape[:2])
        
        # Find the whitest cluster
        # In LAB, L is lightness (0-100), higher values are closer to white
        whitest_cluster = np.argmax(centers[:, 0])
        
        # Find the second whitest cluster (for shadowy parts)
        sorted_indices = np.argsort(centers[:, 0])
        second_whitest = sorted_indices[-2]
        
        # Create a mask for both the whitest and second whitest clusters
        white_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        white_mask[labels_reshaped == whitest_cluster] = 255
        
        # Add the second whitest cluster if it's sufficiently light
        if centers[second_whitest, 0] > 150:  # Threshold for considering it part of white
            white_mask[labels_reshaped == second_whitest] = 255
        
        # Apply morphological operations to clean the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        
        # Find contours in the white mask
        white_contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter out small contours and non-circular shapes
        white_regions = []
        circular_regions = []
        for contour in white_contours:
            area = cv2.contourArea(contour)
            if area > 1000:  # Minimum area threshold
                # Calculate circularity
                perimeter = cv2.arcLength(contour, True)
                circularity = 0
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                
                # Add to white regions for visualization
                white_regions.append(contour)
                
                # Check if shape is circular (circularity close to 1.0)
                if circularity > 0.6:  # Slightly lower threshold for circularity to catch more balloons
                    circular_regions.append(contour)
                    
                    # Draw the circular contour on the display frame
                    cv2.drawContours(display_frame, [contour], 0, (0, 255, 0), 2)  # Green outline
                    
                    # Copy only the circular regions to the output frame
                    mask = np.zeros_like(white_mask)
                    cv2.drawContours(mask, [contour], 0, 255, -1)
                    output_frame[mask == 255] = image[mask == 255]
                    
                    # Add a label
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        cv2.putText(display_frame, f"Balloon ({circularity:.2f})", (cx - 70, cy), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                        cv2.putText(output_frame, f"Balloon ({circularity:.2f})", (cx - 70, cy), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                else:
                    # Draw non-circular contours in a different color
                    cv2.drawContours(display_frame, [contour], 0, (0, 165, 255), 1)  # Orange outline
        
        # Create a colored overlay to highlight circular areas
        overlay = np.zeros_like(image)
        cv2.drawContours(overlay, circular_regions, -1, (0, 255, 0), -1)  # Green fill
        
        # Blend the original image with the overlay
        alpha = 0.3  # Transparency factor
        mask = white_mask > 0
        display_frame[mask] = cv2.addWeighted(image[mask], 1 - alpha, overlay[mask], alpha, 0)
        
        # Also show the mask in corners of the frame
        h, w = white_mask.shape
        scale = 0.2  # Scale factor for the small mask
        small_mask = cv2.resize(white_mask, (int(w * scale), int(h * scale)))
        
        # Convert the mask to a colored image
        small_mask_color = cv2.cvtColor(small_mask, cv2.COLOR_GRAY2BGR)
        
        # Place the small mask in the bottom-right corner
        h_display, w_display = display_frame.shape[:2]
        h_small, w_small = small_mask_color.shape[:2]
        display_frame[h_display - h_small:, w_display - w_small:] = small_mask_color
        
        # Display FPS on the frame
        fps_text = f"FPS: {int(self.fps)}"
        cv2.putText(display_frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                    1, (0, 255, 0), 2)
        cv2.putText(output_frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                    1, (0, 255, 0), 2)
        
        # Display count of circular objects
        circle_count_text = f"Balloons: {len(circular_regions)}"
        cv2.putText(display_frame, circle_count_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 
                    1, (0, 255, 0), 2)
        cv2.putText(output_frame, circle_count_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 
                    1, (0, 255, 0), 2)
        
        # Store the processed frame for display (use the display frame for debugging)
        self.processed_frame = display_frame
        
        # Return only circular regions
        return circular_regions 