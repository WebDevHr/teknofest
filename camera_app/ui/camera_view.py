#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Camera View Component
-------------------
Component for displaying camera feed.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QSize, QRect
from PyQt5.QtGui import QPixmap, QImage, QPainter

class CameraView(QWidget):
    """
    Component for displaying camera feed.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("border: 2px solid #555555; background-color: #2E2E2E;")
        self.current_pixmap = None
        self.aspect_ratio = 4/3  # Default aspect ratio (4:3)
        
    def update_frame(self, q_image):
        """Update the displayed frame with a new QImage."""
        # Store the original image dimensions for aspect ratio calculation
        if not hasattr(self, 'original_size'):
            self.original_size = q_image.size()
            self.aspect_ratio = self.original_size.width() / self.original_size.height()
        
        # Convert QImage to QPixmap only once
        self.current_pixmap = QPixmap.fromImage(q_image)
        
        # Force a repaint to display the new frame
        self.update()
    
    def paintEvent(self, event):
        """Override paintEvent to handle custom drawing."""
        super().paintEvent(event)
        
        if self.current_pixmap is None:
            return
            
        # Create a painter for this widget
        painter = QPainter(self)
        
        # Calculate the size to display the image while maintaining aspect ratio
        widget_size = self.size()
        
        # Calculate the target size based on the widget size and aspect ratio
        target_width = widget_size.width()
        target_height = int(target_width / self.aspect_ratio)
        
        if target_height > widget_size.height():
            target_height = widget_size.height()
            target_width = int(target_height * self.aspect_ratio)
        
        # Calculate position to center the image
        x = (widget_size.width() - target_width) // 2
        y = (widget_size.height() - target_height) // 2
        
        # Scale the pixmap
        scaled_pixmap = self.current_pixmap.scaled(
            target_width, 
            target_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # Draw the pixmap
        painter.drawPixmap(x, y, scaled_pixmap) 