#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Window
----------
Main window for the camera application.
"""

import sys
import os
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

from services.logger_service import LoggerService
from services.camera_service import CameraService
from services.yolo_service import YoloService
from services.shape_detection_service import ShapeDetectionService
from services.roboflow_service import RoboflowService
from ui.sidebar import LogSidebar, MenuSidebar
from ui.camera_view import CameraView
from ui.shape_dialog import ShapeDetectionDialog

class MainWindow(QMainWindow):
    """
    Main window for the camera application.
    Implements the Facade pattern to coordinate components.
    """
    
    def __init__(self):
        super().__init__()
        
        # Get logger service
        self.logger = LoggerService()
        
        # Initialize UI components
        self.init_ui()
        
        # Initialize camera service
        self.init_camera()
        
        # Show the window maximized
        self.showMaximized()
        
        # Position the toggle buttons after showing the window
        self.update_toggle_button_positions()
        
    def init_ui(self):
        """Initialize the user interface components."""
        # Set window properties
        self.setWindowTitle("Modern Camera App")
        self.apply_styles()
        
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create camera view
        self.camera_view = CameraView()
        
        # Create left sidebar (Log Window)
        self.log_sidebar = LogSidebar(self)
        self.log_sidebar.clear_button.clicked.connect(self.on_clear_log)
        
        # Connect logger signals to log sidebar
        self.logger.log_added.connect(self.log_sidebar.add_log)
        
        # Create right sidebar (Menu)
        self.menu_sidebar = MenuSidebar(self)
        
        # Connect menu button signals
        self.menu_sidebar.settings_button.clicked.connect(self.on_settings_clicked)
        self.menu_sidebar.capture_button.clicked.connect(self.on_capture_clicked)
        self.menu_sidebar.save_button.clicked.connect(self.on_save_clicked)
        self.menu_sidebar.yolo_button.clicked.connect(self.on_yolo_clicked)
        self.menu_sidebar.shape_button.clicked.connect(self.on_shape_clicked)
        self.menu_sidebar.roboflow_button.clicked.connect(self.on_roboflow_clicked)
        self.menu_sidebar.exit_button.clicked.connect(self.close)
        
        # Add widgets to main layout
        self.main_layout.addWidget(self.log_sidebar)
        self.main_layout.addWidget(self.camera_view)
        self.main_layout.addWidget(self.menu_sidebar)
        
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
        
        # Connect sidebar animation signals
        self.log_sidebar.animation_value_changed.connect(self.update_toggle_button_positions)
        self.menu_sidebar.animation_value_changed.connect(self.update_toggle_button_positions)
    
    def apply_styles(self):
        """Apply styles to the application."""
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
    
    def init_camera(self):
        """Initialize the camera service."""
        self.camera_service = CameraService()
        
        # Connect camera signals
        self.camera_service.frame_ready.connect(self.camera_view.update_frame)
        self.camera_service.camera_error.connect(self.on_camera_error)
        
        # Initialize and start camera
        if not self.camera_service.initialize():
            self.camera_view.setText("Camera not available")
            return
            
        # Use a lower FPS for better performance
        self.camera_service.start(fps=24)
    
    def on_camera_error(self, error_message):
        """Handle camera errors."""
        self.logger.error(f"Camera error: {error_message}")
        QMessageBox.critical(self, "Camera Error", error_message)
    
    def toggle_left_sidebar(self):
        """Toggle the visibility of the left sidebar."""
        is_open = self.log_sidebar.toggle()
        
        # Update button text
        if is_open:
            self.left_toggle_btn.setText("Hide Logs")
        else:
            self.left_toggle_btn.setText("Show Logs")
    
    def toggle_right_sidebar(self):
        """Toggle the visibility of the right sidebar."""
        self.menu_sidebar.toggle()
    
    def update_toggle_button_positions(self):
        """Update the positions of the toggle buttons."""
        # Position left toggle button
        left_x = self.log_sidebar.width() + 10
        self.left_toggle_btn.move(left_x, 10)
        
        # Position right toggle button
        right_x = self.width() - self.menu_sidebar.width() - self.right_toggle_btn.width() - 10
        self.right_toggle_btn.move(right_x, 10)
    
    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        self.update_toggle_button_positions()
    
    def on_clear_log(self):
        """Handle Clear Log button click."""
        self.log_sidebar.clear_logs()
        self.logger.clear()
    
    def on_settings_clicked(self):
        """Handle Settings button click."""
        self.logger.info("Settings button clicked")
    
    def on_capture_clicked(self):
        """Handle Capture button click."""
        filename = self.camera_service.capture_image()
        if filename:
            self.logger.info(f"Image captured and saved as {filename}")
    
    def on_save_clicked(self):
        """Handle Save button click."""
        self.logger.info("Save button clicked (functionality not implemented)")
    
    def on_yolo_clicked(self):
        """Handle YOLO button click."""
        button = self.menu_sidebar.yolo_button
        
        if button.isChecked():
            # İlk kez tıklandıysa YOLO servisini başlat
            if not hasattr(self, 'yolo_service'):
                if not self.init_yolo():
                    button.setChecked(False)
                    return
            
            # YOLO tespitini başlat
            self.yolo_service.start()
            self.logger.info("YOLO detection started")
            button.setText("Stop Detection")
        else:
            # YOLO tespitini durdur
            if hasattr(self, 'yolo_service'):
                self.yolo_service.stop()
                self.logger.info("YOLO detection stopped")
            button.setText("YOLO Detection")
    
    def init_yolo(self):
        """Initialize the YOLO service."""
        model_path = "C:\\Users\\USER\\Desktop\\pyqt\\camera_app\\models\\best(v8n).pt"
        self.yolo_service = YoloService(model_path)
        
        # YOLO servisini kamera servisine bağla
        self.camera_service.set_yolo_service(self.yolo_service)
        
        # YOLO modelini başlat
        if not self.yolo_service.initialize():
            self.logger.error("Failed to initialize YOLO model")
            QMessageBox.warning(self, "YOLO Error", "Failed to initialize YOLO model. Check if the model file exists.")
            return False
        
        return True
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Release camera resources
        if hasattr(self, 'camera_service'):
            self.camera_service.release()
            
        self.logger.info("Application closed")
        event.accept()
    
    def init_shape_detection(self):
        """Initialize the shape detection service."""
        self.shape_detection_service = ShapeDetectionService()
        
        # Şekil tespiti servisini kamera servisine bağla
        self.camera_service.set_shape_detection_service(self.shape_detection_service)
        
        return True
    
    def on_shape_clicked(self):
        """Handle Shape Detection button click."""
        button = self.menu_sidebar.shape_button
        
        if button.isChecked():
            # İlk kez tıklandıysa şekil tespiti servisini başlat
            if not hasattr(self, 'shape_detection_service'):
                if not self.init_shape_detection():
                    button.setChecked(False)
                    return
            
            # Şekil tespitini başlat
            self.shape_detection_service.start()
            self.logger.info("Shape detection started")
            button.setText("Stop Detection")
        else:
            # Şekil tespitini durdur
            if hasattr(self, 'shape_detection_service'):
                self.shape_detection_service.stop()
                self.logger.info("Shape detection stopped")
            button.setText("Shape Detection")
    
    def init_roboflow(self):
        """Initialize the Roboflow service."""
        # Tam yolu belirtelim
        model_path = "C:\\Users\\USER\\Desktop\\pyqt\\camera_app\\models\\engagement-best.pt"
        
        # Dosyanın varlığını kontrol edelim
        if not os.path.exists(model_path):
            self.logger.error(f"Roboflow model not found at: {model_path}")
            QMessageBox.warning(self, "Roboflow Error", f"Roboflow model not found at: {model_path}\nPlease make sure the model file exists.")
            return False
        
        self.roboflow_service = RoboflowService(model_path)
        
        # Roboflow servisini kamera servisine bağla
        self.camera_service.set_roboflow_service(self.roboflow_service)
        
        # Roboflow modelini başlat
        if not self.roboflow_service.initialize():
            self.logger.error("Failed to initialize Roboflow model")
            QMessageBox.warning(self, "Roboflow Error", "Failed to initialize Roboflow model. Check if the model file is valid.")
            return False
        
        return True
    
    def on_roboflow_clicked(self):
        """Handle Roboflow button click."""
        button = self.menu_sidebar.roboflow_button
        
        if button.isChecked():
            # İlk kez tıklandıysa Roboflow servisini başlat
            if not hasattr(self, 'roboflow_service'):
                if not self.init_roboflow():
                    button.setChecked(False)
                    return
            
            # Roboflow tespitini başlat
            self.roboflow_service.start()
            self.logger.info("Roboflow detection started")
            button.setText("Stop Detection")
        else:
            # Roboflow tespitini durdur
            if hasattr(self, 'roboflow_service'):
                self.roboflow_service.stop()
                self.logger.info("Roboflow detection stopped")
            button.setText("Roboflow Detection") 