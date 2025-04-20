#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modern Camera Application with PyQt5
------------------------------------
A full-screen camera application with animated sidebars,
logging functionality, and image capture capabilities.
"""

import sys
import cv2
import time
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QPushButton, QTextEdit, QLabel, QMessageBox,
                            QHBoxLayout, QFrame)
from PyQt5.QtCore import (Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve,
                         QSize, pyqtSlot)
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QColor


class MainWindow(QMainWindow):
    """Main application window for the camera app."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize UI components
        self.init_ui()
        
        # Initialize camera
        self.init_camera()
        
        # Start the camera timer
        self.start_camera_timer()
        
    def init_ui(self):
        """Initialize the user interface components."""
        # Set window properties
        self.setWindowTitle("Modern Camera App")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2E2E2E;
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
            QPushButton:pressed {
                background-color: #388E3C;
            }
            QTextEdit {
                background-color: #3E3E3E;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
                font-family: 'Consolas', monospace;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)
        
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create camera display
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("border: 2px solid #555555;")
        
        # Create left sidebar (Log Window)
        self.left_sidebar = QWidget()
        self.left_sidebar.setFixedWidth(0)  # Initially hidden
        self.left_sidebar.setStyleSheet("background-color: #333333;")
        
        left_layout = QVBoxLayout(self.left_sidebar)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Clear log button
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(self.clear_log)
        left_layout.addWidget(self.clear_log_btn)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        left_layout.addWidget(self.log_text)
        
        # Create right sidebar (Menu)
        self.right_sidebar = QWidget()
        self.right_sidebar.setFixedWidth(0)  # Initially hidden
        self.right_sidebar.setStyleSheet("background-color: #333333;")
        
        right_layout = QVBoxLayout(self.right_sidebar)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setAlignment(Qt.AlignTop)
        
        # Menu buttons
        self.settings_btn = QPushButton("Settings")
        self.capture_btn = QPushButton("Capture")
        self.save_btn = QPushButton("Save")
        self.exit_btn = QPushButton("Exit")
        
        # Connect button signals
        self.settings_btn.clicked.connect(self.on_settings_clicked)
        self.capture_btn.clicked.connect(self.on_capture_clicked)
        self.save_btn.clicked.connect(self.on_save_clicked)
        self.exit_btn.clicked.connect(self.close)
        
        # Add buttons to right sidebar
        right_layout.addWidget(self.settings_btn)
        right_layout.addWidget(self.capture_btn)
        right_layout.addWidget(self.save_btn)
        right_layout.addWidget(self.exit_btn)
        right_layout.addStretch()
        
        # Add widgets to main layout
        self.main_layout.addWidget(self.left_sidebar)
        self.main_layout.addWidget(self.camera_label)
        self.main_layout.addWidget(self.right_sidebar)
        
        # Create toggle buttons for sidebars
        self.left_toggle_btn = QPushButton("Show Logs")
        self.left_toggle_btn.setFixedSize(100, 40)
        self.left_toggle_btn.clicked.connect(self.toggle_left_sidebar)
        
        self.right_toggle_btn = QPushButton("Menu")
        self.right_toggle_btn.setFixedSize(100, 40)
        self.right_toggle_btn.clicked.connect(self.toggle_right_sidebar)
        
        # Position toggle buttons
        self.left_toggle_btn.setParent(self)
        self.right_toggle_btn.setParent(self)
        
        # Initialize sidebar states
        self.left_sidebar_open = False
        self.right_sidebar_open = False
        
        # Show the window maximized
        self.showMaximized()
        
        # Position the toggle buttons after showing the window
        self.update_toggle_button_positions()
        
    def init_camera(self):
        """Initialize the camera capture."""
        self.capture = cv2.VideoCapture(0)
        
        if not self.capture.isOpened():
            QMessageBox.critical(self, "Camera Error", 
                                "Could not open camera. Please check your camera connection.")
            self.camera_label.setText("Camera not available")
            self.camera_available = False
        else:
            self.camera_available = True
            self.log_message("Camera initialized successfully")
    
    def start_camera_timer(self):
        """Start the timer for camera updates."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(33)  # ~30 FPS
    
    def update_frame(self):
        """Update the camera frame."""
        if not self.camera_available:
            return
            
        ret, frame = self.capture.read()
        if ret:
            # Convert the frame to RGB format
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Get frame dimensions
            height, width, channels = frame.shape
            
            # Create QImage from frame
            bytes_per_line = channels * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Create pixmap from QImage
            pixmap = QPixmap.fromImage(q_image)
            
            # Calculate the size to display the image while maintaining aspect ratio
            label_size = self.camera_label.size()
            pixmap = pixmap.scaled(
                label_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Set the pixmap to the label
            self.camera_label.setPixmap(pixmap)
            
            # Center the pixmap in the label
            self.camera_label.setAlignment(Qt.AlignCenter)
        else:
            self.log_message("Error capturing frame")
    
    def toggle_left_sidebar(self):
        """Toggle the visibility of the left sidebar with animation."""
        target_width = 300 if not self.left_sidebar_open else 0
        
        # Create animation
        self.left_anim = QPropertyAnimation(self.left_sidebar, b"minimumWidth")
        self.left_anim.setDuration(300)
        self.left_anim.setStartValue(self.left_sidebar.width())
        self.left_anim.setEndValue(target_width)
        self.left_anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Update button text
        if not self.left_sidebar_open:
            self.left_toggle_btn.setText("Hide Logs")
        else:
            self.left_toggle_btn.setText("Show Logs")
        
        # Start animation
        self.left_anim.start()
        
        # Update state
        self.left_sidebar_open = not self.left_sidebar_open
        
        # Update toggle button position during animation
        self.left_anim.valueChanged.connect(self.update_toggle_button_positions)
    
    def toggle_right_sidebar(self):
        """Toggle the visibility of the right sidebar with animation."""
        target_width = 250 if not self.right_sidebar_open else 0
        
        # Create animation
        self.right_anim = QPropertyAnimation(self.right_sidebar, b"minimumWidth")
        self.right_anim.setDuration(300)
        self.right_anim.setStartValue(self.right_sidebar.width())
        self.right_anim.setEndValue(target_width)
        self.right_anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Start animation
        self.right_anim.start()
        
        # Update state
        self.right_sidebar_open = not self.right_sidebar_open
        
        # Update toggle button position during animation
        self.right_anim.valueChanged.connect(self.update_toggle_button_positions)
    
    def update_toggle_button_positions(self):
        """Update the positions of the toggle buttons."""
        # Position left toggle button
        left_x = self.left_sidebar.width() + 10
        self.left_toggle_btn.move(left_x, 10)
        
        # Position right toggle button
        right_x = self.width() - self.right_sidebar.width() - self.right_toggle_btn.width() - 10
        self.right_toggle_btn.move(right_x, 10)
    
    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        self.update_toggle_button_positions()
    
    def log_message(self, message):
        """Add a timestamped message to the log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp}: {message}"
        self.log_text.append(log_entry)
        
        # Auto-scroll to the bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """Clear the log text area."""
        self.log_text.clear()
        self.log_message("Log cleared")
    
    def on_settings_clicked(self):
        """Handle Settings button click."""
        self.log_message("Settings button clicked")
    
    def on_capture_clicked(self):
        """Handle Capture button click to save the current frame."""
        if not self.camera_available:
            self.log_message("Cannot capture: Camera not available")
            return
            
        # Create directory if it doesn't exist
        if not os.path.exists("captures"):
            os.makedirs("captures")
            
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captures/capture_{timestamp}.png"
        
        # Capture frame
        ret, frame = self.capture.read()
        if ret:
            # Save the image
            cv2.imwrite(filename, frame)
            self.log_message(f"Image captured and saved as {filename}")
        else:
            self.log_message("Failed to capture image")
    
    def on_save_clicked(self):
        """Handle Save button click (placeholder)."""
        self.log_message("Save button clicked (functionality not implemented)")
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Release camera resources
        if hasattr(self, 'capture') and self.capture.isOpened():
            self.capture.release()
            
        # Stop timer
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
            
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_()) 