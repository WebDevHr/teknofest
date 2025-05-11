#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Servo Control Dialog
------------------
Dialog for manually controlling the servo motors.
"""

import sys
import time
from PyQt5.QtWidgets import (QDialog, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, 
                            QGridLayout, QGroupBox, QSlider, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette, QColor, QFont

class ServoControlDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.active_keys = set()  # Track which keys are currently pressed
        self.repeat_timer = QTimer()
        self.repeat_timer.timeout.connect(self.process_active_keys)
        self.repeat_timer.setInterval(30)  # Repeat every 30ms
        
        # Parent window for accessing pan_tilt_service
        self.parent = parent
        
        # Set dialog properties
        self.setWindowTitle('Manuel Servo Kontrolü')
        self.setMinimumWidth(400)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        # Check for parent theme if available
        self.is_dark_theme = True  # Default to dark theme
        if parent and hasattr(parent, 'current_theme'):
            self.is_dark_theme = parent.current_theme == "dark"
        
        # Setup the UI
        self.initUI()
        
        # Set focus to enable keyboard events
        self.setFocus()
        self.setFocusPolicy(Qt.StrongFocus)
        
    def initUI(self):
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Apply the style based on theme
        self.apply_theme_style()
        
        # Speed control slider
        speed_group = QGroupBox("Hareket Hızı")
        speed_layout = QVBoxLayout()
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 50)  # 1 = slowest, 50 = fastest
        self.speed_slider.setValue(10)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(5)
        self.apply_slider_style()
        
        self.speed_label = QLabel("Hareket Hızı: 10")
        self.speed_slider.valueChanged.connect(self.update_speed_label)
        
        speed_layout.addWidget(self.speed_label)
        speed_layout.addWidget(self.speed_slider)
        speed_group.setLayout(speed_layout)
        
        # Servo control group
        control_group = QGroupBox("Servo Kontrolü")
        control_layout = QGridLayout()
        control_layout.setSpacing(5)
        
        # Control buttons - daha küçük
        self.up_button = QPushButton("▲")
        self.up_button.setFixedSize(50, 50)
        self.up_button.pressed.connect(lambda: self.on_button_pressed("up"))
        self.up_button.released.connect(lambda: self.on_button_released("up"))
        
        self.left_button = QPushButton("◀")
        self.left_button.setFixedSize(50, 50)
        self.left_button.pressed.connect(lambda: self.on_button_pressed("left"))
        self.left_button.released.connect(lambda: self.on_button_released("left"))
        
        self.right_button = QPushButton("▶")
        self.right_button.setFixedSize(50, 50)
        self.right_button.pressed.connect(lambda: self.on_button_pressed("right"))
        self.right_button.released.connect(lambda: self.on_button_released("right"))
        
        self.down_button = QPushButton("▼")
        self.down_button.setFixedSize(50, 50)
        self.down_button.pressed.connect(lambda: self.on_button_pressed("down"))
        self.down_button.released.connect(lambda: self.on_button_released("down"))
        
        # Apply button styles
        self.apply_control_button_style(self.up_button)
        self.apply_control_button_style(self.left_button)
        self.apply_control_button_style(self.right_button)
        self.apply_control_button_style(self.down_button)
        
        # Add buttons to grid
        control_layout.addWidget(self.up_button, 0, 1, 1, 1, Qt.AlignCenter)
        control_layout.addWidget(self.left_button, 1, 0, 1, 1, Qt.AlignCenter)
        control_layout.addWidget(self.right_button, 1, 2, 1, 1, Qt.AlignCenter)
        control_layout.addWidget(self.down_button, 2, 1, 1, 1, Qt.AlignCenter)
        
        # Her buton için alan ayarla
        control_layout.setRowMinimumHeight(0, 70)
        control_layout.setRowMinimumHeight(1, 70)
        control_layout.setRowMinimumHeight(2, 70)
        control_layout.setColumnMinimumWidth(0, 70)
        control_layout.setColumnMinimumWidth(1, 70)
        control_layout.setColumnMinimumWidth(2, 70)
        
        control_group.setLayout(control_layout)
        
        # Keyboard control info
        keyboard_group = QGroupBox("Klavye Kontrolü")
        keyboard_layout = QVBoxLayout()
        keyboard_info = QLabel("Ok tuşlarını kullanarak servoları kontrol edebilirsiniz (sürekli hareket için basılı tutun)")
        keyboard_info.setWordWrap(True)
        keyboard_info.setStyleSheet(self.get_keyboard_info_style())
        keyboard_layout.addWidget(keyboard_info)
        keyboard_group.setLayout(keyboard_layout)
        
        # Status display
        if self.parent and hasattr(self.parent, 'pan_tilt_service') and self.parent.pan_tilt_service.is_connected:
            self.status_label = QLabel("Arduino bağlantısı kullanılıyor")
            self.apply_status_label_style("success")
        else:
            self.status_label = QLabel("Arduino bağlantısı yok - servo kontrolü çalışmayacak")
            self.apply_status_label_style("error")
        
        # Add all components to main layout
        main_layout.addWidget(speed_group)
        main_layout.addWidget(control_group)
        main_layout.addWidget(keyboard_group)
        main_layout.addWidget(self.status_label)
        
        # Set main layout
        self.setLayout(main_layout)
        
        # Pencereyi otomatik boyutlandır
        self.adjustSize()
    
    def apply_theme_style(self):
        """Apply styles based on current theme."""
        if self.is_dark_theme:
            # Dark theme
            self.setStyleSheet("""
                QDialog {
                    background-color: #2D2D30;
                    color: #F1F1F1;
                }
                QGroupBox {
                    background-color: #333337;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    margin-top: 12px;
                    color: #F1F1F1;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 4px;
                    background-color: #333337;
                }
                QLabel {
                    color: #F1F1F1;
                }
                QPushButton {
                    background-color: #444444;
                    color: #F1F1F1;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #555555;
                }
                QPushButton:pressed {
                    background-color: #666666;
                }
            """)
        else:
            # Light theme
            self.setStyleSheet("""
                QDialog {
                    background-color: #F5F5F5;
                    color: #333333;
                }
                QGroupBox {
                    background-color: #FFFFFF;
                    border: 1px solid #DDDDDD;
                    border-radius: 4px;
                    margin-top: 12px;
                    color: #333333;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 4px;
                    background-color: #FFFFFF;
                }
                QLabel {
                    color: #333333;
                }
                QPushButton {
                    background-color: #EEEEEE;
                    color: #333333;
                    border: 1px solid #CCCCCC;
                    border-radius: 4px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #E5E5E5;
                }
                QPushButton:pressed {
                    background-color: #D5D5D5;
                }
            """)
    
    def apply_slider_style(self):
        """Apply style to the slider based on theme."""
        if self.is_dark_theme:
            self.speed_slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    border: 1px solid #999999;
                    background: #333333;
                    height: 10px;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #4CAF50;
                    border: 1px solid #5c5c5c;
                    width: 18px;
                    height: 18px;
                    margin: -5px 0;
                    border-radius: 9px;
                }
                QSlider::handle:horizontal:hover {
                    background: #45a049;
                }
                QSlider::add-page:horizontal {
                    background: #333333;
                    border-radius: 4px;
                }
                QSlider::sub-page:horizontal {
                    background: #00796B;
                    border-radius: 4px;
                }
            """)
        else:
            self.speed_slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    border: 1px solid #BBBBBB;
                    background: #DDDDDD;
                    height: 10px;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #4CAF50;
                    border: 1px solid #AAAAAA;
                    width: 18px;
                    height: 18px;
                    margin: -5px 0;
                    border-radius: 9px;
                }
                QSlider::handle:horizontal:hover {
                    background: #45a049;
                }
                QSlider::add-page:horizontal {
                    background: #DDDDDD;
                    border-radius: 4px;
                }
                QSlider::sub-page:horizontal {
                    background: #00796B;
                    border-radius: 4px;
                }
            """)
    
    def apply_control_button_style(self, button):
        """Apply style to control buttons based on theme."""
        if self.is_dark_theme:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #424242;
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4A4A4A;
                }
                QPushButton:pressed {
                    background-color: #666666;
                }
            """)
        else:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #EEEEEE;
                    color: #333333;
                    border: 1px solid #CCCCCC;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #E5E5E5;
                }
                QPushButton:pressed {
                    background-color: #D5D5D5;
                }
            """)
    
    def apply_status_label_style(self, status="normal"):
        """Apply style to status label based on connection status."""
        base_style = """
            font-size: 13px;
            padding: 5px;
            border-radius: 3px;
        """
        
        if status == "success":
            # Green for success
            self.status_label.setStyleSheet(base_style + """
                background-color: #43A047;
                color: white;
            """)
        elif status == "error":
            # Red for error
            self.status_label.setStyleSheet(base_style + """
                background-color: #E53935;
                color: white;
            """)
        else:
            # Gray for normal
            self.status_label.setStyleSheet(base_style + """
                background-color: #757575;
                color: white;
            """)
    
    def get_keyboard_info_style(self):
        """Get style for keyboard info label."""
        if self.is_dark_theme:
            return """
                background-color: #3E3E42;
                color: #F1F1F1;
                padding: 5px;
                border-radius: 3px;
                border: 1px solid #555555;
            """
        else:
            return """
                background-color: #F0F0F0;
                color: #333333;
                padding: 5px;
                border-radius: 3px;
                border: 1px solid #CCCCCC;
            """
    
    def update_speed_label(self, value):
        """Update the speed label when slider value changes."""
        self.speed_label.setText(f"Hareket Hızı: {value}")
    
    def on_button_pressed(self, direction):
        """Handle control button press."""
        # Add the direction to active keys
        self.active_keys.add(direction)
        
        # Start the repeat timer if not already running
        if not self.repeat_timer.isActive():
            self.repeat_timer.start()
        
        # Process the keys immediately
        self.process_active_keys()
    
    def on_button_released(self, direction):
        """Handle control button release."""
        # Remove the direction from active keys
        if direction in self.active_keys:
            self.active_keys.remove(direction)
        
        # Stop the timer if no keys are pressed
        if not self.active_keys and self.repeat_timer.isActive():
            self.repeat_timer.stop()
    
    def process_active_keys(self):
        """Process all active keys to move servos accordingly."""
        if not self.parent or not hasattr(self.parent, 'pan_tilt_service'):
            self.status_label.setText("Arduino bağlantısı yok - servo kontrolü çalışmayacak")
            self.apply_status_label_style("error")
            return
            
        speed = self.speed_slider.value() / 10.0  # Scale speed (1-50 -> 0.1-5.0)
        
        # Calculate movement for each active direction
        pan_delta = 0
        tilt_delta = 0
        
        if "up" in self.active_keys:
            pan_delta += speed
        if "down" in self.active_keys:
            pan_delta -= speed
        if "left" in self.active_keys:
            tilt_delta -= speed
        if "right" in self.active_keys:
            tilt_delta += speed
        
        # Move servos if needed
        if pan_delta != 0 or tilt_delta != 0:
            self.parent.pan_tilt_service.move_by(pan_delta, tilt_delta)
            current_pan = self.parent.pan_tilt_service.pan_angle
            current_tilt = self.parent.pan_tilt_service.tilt_angle
            self.status_label.setText(f"Pan: {current_pan:.1f}°, Tilt: {current_tilt:.1f}°")
            self.apply_status_label_style("success")
    
    def keyPressEvent(self, event):
        """Handle keyboard input."""
        key = event.key()
        
        # Map arrow keys to directions
        if key == Qt.Key_Up and not event.isAutoRepeat():
            self.on_button_pressed("up")
        elif key == Qt.Key_Down and not event.isAutoRepeat():
            self.on_button_pressed("down")
        elif key == Qt.Key_Left and not event.isAutoRepeat():
            self.on_button_pressed("left")
        elif key == Qt.Key_Right and not event.isAutoRepeat():
            self.on_button_pressed("right")
        else:
            # Let the base class handle other keys
            super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """Handle keyboard release."""
        key = event.key()
        
        # Map arrow keys to directions
        if key == Qt.Key_Up and not event.isAutoRepeat():
            self.on_button_released("up")
        elif key == Qt.Key_Down and not event.isAutoRepeat():
            self.on_button_released("down")
        elif key == Qt.Key_Left and not event.isAutoRepeat():
            self.on_button_released("left")
        elif key == Qt.Key_Right and not event.isAutoRepeat():
            self.on_button_released("right")
        else:
            # Let the base class handle other keys
            super().keyReleaseEvent(event) 