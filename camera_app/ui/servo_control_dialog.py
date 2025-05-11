#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Servo Control Dialog
------------------
Dialog for manually controlling the servo motors.
"""

import sys
import serial
import time
from PyQt5.QtWidgets import (QDialog, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QComboBox, 
                            QGridLayout, QGroupBox, QSlider, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette, QColor, QFont

class ServoControlDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.serial_connection = None
        self.active_keys = set()  # Track which keys are currently pressed
        self.repeat_timer = QTimer()
        self.repeat_timer.timeout.connect(self.process_active_keys)
        self.repeat_timer.setInterval(30)  # Repeat every 30ms
        
        # Set dialog properties
        self.setWindowTitle('Manuel Servo Kontrolü')
        self.setMinimumWidth(400)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
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
        
        # Arka plan rengi için stil
        self.setStyleSheet("""
            QDialog {
                background-color: #212121;
                color: white;
            }
            QLabel {
                color: white;
            }
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 1px solid #444444;
                border-radius: 5px;
                margin-top: 1.5ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
                background-color: #212121;
            }
        """)
        
        # Serial port connection group
        connection_group = QGroupBox("Seri Bağlantı")
        connection_layout = QHBoxLayout()
        
        # COM port selection
        self.port_label = QLabel("COM Port:")
        self.port_combo = QComboBox()
        self.port_combo.setStyleSheet("""
            QComboBox {
                background-color: #333333;
                color: white;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
                min-width: 100px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #555555;
            }
            QComboBox:hover {
                border: 1px solid #888888;
            }
        """)
        
        # Find available COM ports (Windows-specific)
        for i in range(1, 10):
            self.port_combo.addItem(f"COM{i}")
            
        self.connect_button = QPushButton("Bağlan")
        self.connect_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 3px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #388e3c;
            }
        """)
        self.connect_button.clicked.connect(self.toggle_connection)
        
        # Add widgets to connection layout
        connection_layout.addWidget(self.port_label)
        connection_layout.addWidget(self.port_combo)
        connection_layout.addWidget(self.connect_button)
        connection_group.setLayout(connection_layout)
        
        # Speed control slider
        speed_group = QGroupBox("Hareket Hızı")
        speed_layout = QVBoxLayout()
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 50)  # 1 = slowest, 50 = fastest
        self.speed_slider.setValue(10)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(5)
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
        self.up_button = QPushButton()
        self.up_button.setText("▲")
        self.up_button.setFont(QFont("Arial", 16, QFont.Bold))
        self.up_button.setFixedSize(60, 60)
        self.up_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #666666;
            }
        """)
        self.up_button.pressed.connect(lambda: self.button_pressed("up"))
        self.up_button.released.connect(lambda: self.button_released("up"))
        
        self.down_button = QPushButton()
        self.down_button.setText("▼")
        self.down_button.setFont(QFont("Arial", 16, QFont.Bold))
        self.down_button.setFixedSize(60, 60)
        self.down_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #666666;
            }
        """)
        self.down_button.pressed.connect(lambda: self.button_pressed("down"))
        self.down_button.released.connect(lambda: self.button_released("down"))
        
        self.left_button = QPushButton()
        self.left_button.setText("◄")
        self.left_button.setFont(QFont("Arial", 16, QFont.Bold))
        self.left_button.setFixedSize(60, 60)
        self.left_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #666666;
            }
        """)
        self.left_button.pressed.connect(lambda: self.button_pressed("left"))
        self.left_button.released.connect(lambda: self.button_released("left"))
        
        self.right_button = QPushButton()
        self.right_button.setText("►")
        self.right_button.setFont(QFont("Arial", 16, QFont.Bold))
        self.right_button.setFixedSize(60, 60)
        self.right_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #666666;
            }
        """)
        self.right_button.pressed.connect(lambda: self.button_pressed("right"))
        self.right_button.released.connect(lambda: self.button_released("right"))
        
        # Add buttons to control layout with proper spacing
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
        keyboard_info.setStyleSheet("""
            color: #E0E0E0;
            padding: 5px;
            background-color: #333333;
            border-radius: 3px;
        """)
        keyboard_layout.addWidget(keyboard_info)
        keyboard_group.setLayout(keyboard_layout)
        
        # Status display
        self.status_label = QLabel("Bağlı değil")
        self.status_label.setStyleSheet("""
            padding: 5px;
            border-radius: 3px;
            background-color: #333333;
            color: white;
            font-weight: bold;
        """)
        
        # Add all components to main layout
        main_layout.addWidget(connection_group)
        main_layout.addWidget(speed_group)
        main_layout.addWidget(control_group)
        main_layout.addWidget(keyboard_group)
        main_layout.addWidget(self.status_label)
        
        # Disable control buttons initially
        self.set_controls_enabled(False)
        
        # Set main layout
        self.setLayout(main_layout)
        
        # Pencereyi otomatik boyutlandır
        self.adjustSize()
        
    def update_speed_label(self, value):
        self.speed_label.setText(f"Hareket Hızı: {value}")
        
    def button_pressed(self, command):
        if self.serial_connection and self.serial_connection.is_open:
            self.active_keys.add(command)
            self.send_command(command)
            if not self.repeat_timer.isActive():
                self.repeat_timer.start()
    
    def button_released(self, command):
        if command in self.active_keys:
            self.active_keys.remove(command)
        if not self.active_keys and self.repeat_timer.isActive():
            self.repeat_timer.stop()
            
    def process_active_keys(self):
        """Process all currently active keys"""
        for command in self.active_keys:
            self.send_command(command)
        
    def keyPressEvent(self, event):
        """Handle keyboard arrow key presses"""
        if not (self.serial_connection and self.serial_connection.is_open):
            return
            
        key_cmd_map = {
            Qt.Key_Up: "up",
            Qt.Key_Down: "down",
            Qt.Key_Left: "left",
            Qt.Key_Right: "right"
        }
        
        key = event.key()
        if key in key_cmd_map and not event.isAutoRepeat():
            command = key_cmd_map[key]
            self.active_keys.add(command)
            
            # Visual feedback by setting the button down
            button_map = {
                "up": self.up_button,
                "down": self.down_button,
                "left": self.left_button,
                "right": self.right_button
            }
            button_map[command].setDown(True)
            
            # Send command and start repeat timer if needed
            self.send_command(command)
            if not self.repeat_timer.isActive():
                self.repeat_timer.start()
        else:
            super().keyPressEvent(event)
            
    def keyReleaseEvent(self, event):
        """Handle keyboard arrow key releases"""
        if not event.isAutoRepeat():  # Ignore auto-repeat releases
            key_cmd_map = {
                Qt.Key_Up: "up",
                Qt.Key_Down: "down",
                Qt.Key_Left: "left",
                Qt.Key_Right: "right"
            }
            
            key = event.key()
            if key in key_cmd_map:
                command = key_cmd_map[key]
                if command in self.active_keys:
                    self.active_keys.remove(command)
                
                # Visual feedback by releasing the button
                button_map = {
                    "up": self.up_button,
                    "down": self.down_button,
                    "left": self.left_button,
                    "right": self.right_button
                }
                button_map[command].setDown(False)
                
                # Stop timer if no keys are active
                if not self.active_keys and self.repeat_timer.isActive():
                    self.repeat_timer.stop()
        
        super().keyReleaseEvent(event)
            
    def toggle_connection(self):
        if self.serial_connection is None:
            # Connect
            try:
                port = self.port_combo.currentText()
                self.serial_connection = serial.Serial(port, 115200, timeout=0.5)  # Higher baud rate
                time.sleep(2)  # Wait for Arduino to reset
                
                self.connect_button.setText("Bağlantıyı Kes")
                self.connect_button.setStyleSheet("""
                    QPushButton {
                        background-color: #F44336;
                        color: white;
                        border-radius: 3px;
                        padding: 8px 16px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #E53935;
                    }
                    QPushButton:pressed {
                        background-color: #D32F2F;
                    }
                """)
                self.status_label.setText(f"{port} portuna bağlandı")
                self.status_label.setStyleSheet("""
                    padding: 5px;
                    border-radius: 3px;
                    background-color: #333333;
                    color: #4CAF50;
                    font-weight: bold;
                """)
                self.set_controls_enabled(True)
            except Exception as e:
                self.status_label.setText(f"Bağlantı hatası: {str(e)}")
                self.status_label.setStyleSheet("""
                    padding: 5px;
                    border-radius: 3px;
                    background-color: #333333;
                    color: #F44336;
                    font-weight: bold;
                """)
        else:
            # Disconnect
            try:
                self.serial_connection.close()
            except:
                pass
            finally:
                self.serial_connection = None
                self.connect_button.setText("Bağlan")
                self.connect_button.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border-radius: 3px;
                        padding: 8px 16px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QPushButton:pressed {
                        background-color: #388e3c;
                    }
                """)
                self.status_label.setText("Bağlı değil")
                self.status_label.setStyleSheet("""
                    padding: 5px;
                    border-radius: 3px;
                    background-color: #333333;
                    color: white;
                    font-weight: bold;
                """)
                self.set_controls_enabled(False)
    
    def send_command(self, command):
        if self.serial_connection and self.serial_connection.is_open:
            try:
                # Adjust command send rate based on slider
                repeat_count = self.speed_slider.value()
                
                # Send command to Arduino multiple times (faster movement)
                for _ in range(repeat_count):
                    self.serial_connection.write(f"{command}\n".encode())
                
                # Read response (but don't wait too long)
                time.sleep(0.01)
                if self.serial_connection.in_waiting:
                    response = self.serial_connection.readline().decode().strip()
                    self.status_label.setText(response)
                    self.status_label.setStyleSheet("""
                        padding: 5px;
                        border-radius: 3px;
                        background-color: #333333;
                        color: #2196F3;
                        font-weight: bold;
                    """)
            except Exception as e:
                self.status_label.setText(f"Hata: {str(e)}")
                self.status_label.setStyleSheet("""
                    padding: 5px;
                    border-radius: 3px;
                    background-color: #333333;
                    color: #F44336;
                    font-weight: bold;
                """)
    
    def set_controls_enabled(self, enabled):
        button_style_enabled = """
            QPushButton {
                background-color: #444444;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #666666;
            }
        """
        
        button_style_disabled = """
            QPushButton {
                background-color: #333333;
                color: #777777;
                border-radius: 5px;
            }
        """
        
        self.up_button.setEnabled(enabled)
        self.down_button.setEnabled(enabled)
        self.left_button.setEnabled(enabled)
        self.right_button.setEnabled(enabled)
        self.speed_slider.setEnabled(enabled)
        
        # Buton stillerini duruma göre ayarla
        if enabled:
            self.up_button.setStyleSheet(button_style_enabled)
            self.down_button.setStyleSheet(button_style_enabled)
            self.left_button.setStyleSheet(button_style_enabled)
            self.right_button.setStyleSheet(button_style_enabled)
        else:
            self.up_button.setStyleSheet(button_style_disabled)
            self.down_button.setStyleSheet(button_style_disabled)
            self.left_button.setStyleSheet(button_style_disabled)
            self.right_button.setStyleSheet(button_style_disabled)
        
    def closeEvent(self, event):
        # Clean up serial connection on exit
        if self.serial_connection:
            self.serial_connection.close()
        event.accept() 