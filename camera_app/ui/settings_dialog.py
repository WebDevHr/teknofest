#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Settings Dialog
--------------
Dialog for application settings.
"""

import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QFormLayout, QLabel, QComboBox, 
                             QPushButton, QSpinBox, QLineEdit,
                             QTabWidget, QWidget, QCheckBox, 
                             QMessageBox, QGroupBox, QInputDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import cv2
import serial.tools.list_ports
from utils.config import config
from services.logger_service import LoggerService

class SettingsDialog(QDialog):
    """Dialog for changing application settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = LoggerService()
        self.parent = parent
        
        # Set dialog properties
        self.setWindowTitle("Ayarlar")
        self.setMinimumWidth(500)
        self.setMinimumHeight(450)
        
        # Initialize UI components
        self.init_ui()
        
        # Load current settings
        self.load_settings()
    
    def init_ui(self):
        """Initialize the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        # Style tabs for both dark and light themes
        self.tab_widget.setStyleSheet("""
            QTabBar::tab {
                background: palette(mid);
                color: palette(text);
                padding: 6px 12px;
                margin-right: 1px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: palette(window);
                color: palette(text);
                border: 1px solid palette(highlight);
                border-bottom: none;
            }
            QTabBar::tab:!selected {
                border: 1px solid palette(mid);
                border-bottom: 1px solid palette(mid);
            }
            QTabWidget::pane {
                border: 1px solid palette(mid);
                top: -1px;
            }
        """)
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_camera_tab()
        self.create_connection_tab()
        self.create_system_tab()
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Apply button
        self.apply_button = QPushButton("Uygula")
        self.apply_button.clicked.connect(self.apply_settings)
        
        # OK button
        self.ok_button = QPushButton("Tamam")
        self.ok_button.clicked.connect(self.save_and_close)
        
        # Cancel button
        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)
        
        # Add buttons to layout
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.apply_button)
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        
        # Add buttons layout to main layout
        main_layout.addLayout(buttons_layout)
    
    def create_camera_tab(self):
        """Create the camera settings tab."""
        camera_tab = QWidget()
        camera_layout = QVBoxLayout(camera_tab)
        
        # Camera settings group
        camera_group = QGroupBox("Kamera Ayarları")
        camera_form = QFormLayout(camera_group)
        
        # Camera ID
        self.camera_id_spin = QSpinBox()
        self.camera_id_spin.setMinimum(0)
        self.camera_id_spin.setMaximum(10)
        camera_form.addRow("Kamera ID:", self.camera_id_spin)
        
        # Camera resolution
        self.camera_resolution_combo = QComboBox()
        self.populate_resolution_combo()
        camera_form.addRow("Çözünürlük:", self.camera_resolution_combo)
        
        # FPS limit
        self.fps_limit_spin = QSpinBox()
        self.fps_limit_spin.setMinimum(1)
        self.fps_limit_spin.setMaximum(120)
        camera_form.addRow("FPS Limiti:", self.fps_limit_spin)
        
        # Save format
        self.save_format_combo = QComboBox()
        self.save_format_combo.addItems(["JPEG", "PNG", "BMP"])
        camera_form.addRow("Kayıt Formatı:", self.save_format_combo)
        
        # Add camera group to tab layout
        camera_layout.addWidget(camera_group)
        
        # Additional camera options group
        additional_group = QGroupBox("Ek Kamera Seçenekleri")
        additional_form = QFormLayout(additional_group)
        
        # Auto exposure
        self.auto_exposure_check = QCheckBox("Aktif")
        additional_form.addRow("Otomatik Pozlama:", self.auto_exposure_check)
        
        # Auto white balance
        self.auto_wb_check = QCheckBox("Aktif")
        additional_form.addRow("Otomatik Beyaz Dengesi:", self.auto_wb_check)
        
        # Add additional group to tab layout
        camera_layout.addWidget(additional_group)
        
        # Add the tab to tab widget
        self.tab_widget.addTab(camera_tab, "Kamera")
    
    def create_connection_tab(self):
        """Create the connection settings tab."""
        connection_tab = QWidget()
        connection_layout = QVBoxLayout(connection_tab)
        
        # Pan-Tilt servo connection group
        servo_group = QGroupBox("Pan-Tilt Servo Bağlantısı")
        servo_form = QFormLayout(servo_group)
        
        # Serial port - Changed from LineEdit to ComboBox
        self.serial_port_combo = QComboBox()
        self.populate_serial_ports()
        
        # Add refresh button next to the combo
        serial_port_layout = QHBoxLayout()
        serial_port_layout.addWidget(self.serial_port_combo)
        
        refresh_button = QPushButton("Yenile")
        refresh_button.setFixedWidth(80)
        refresh_button.clicked.connect(self.populate_serial_ports)
        serial_port_layout.addWidget(refresh_button)
        
        servo_form.addRow("Seri Port:", serial_port_layout)
        
        # Baud rate
        self.baud_rate_combo = QComboBox()
        self.baud_rate_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        servo_form.addRow("Baud Rate:", self.baud_rate_combo)
        
        # Add servo group to tab layout
        connection_layout.addWidget(servo_group)
        
        # Servo settings group
        servo_settings_group = QGroupBox("Servo Ayarları")
        servo_settings_form = QFormLayout(servo_settings_group)
        
        # Servo center position
        self.pan_center_spin = QSpinBox()
        self.pan_center_spin.setMinimum(0)
        self.pan_center_spin.setMaximum(180)
        self.pan_center_spin.setValue(90)  # Default center
        servo_settings_form.addRow("Pan Merkez Pozisyon:", self.pan_center_spin)
        
        self.tilt_center_spin = QSpinBox()
        self.tilt_center_spin.setMinimum(0)
        self.tilt_center_spin.setMaximum(180)
        self.tilt_center_spin.setValue(90)  # Default center
        servo_settings_form.addRow("Tilt Merkez Pozisyon:", self.tilt_center_spin)
        
        # Pan min/max angle
        self.pan_min_angle_spin = QSpinBox()
        self.pan_min_angle_spin.setMinimum(-180)
        self.pan_min_angle_spin.setMaximum(0)
        servo_settings_form.addRow("Pan Min Açı:", self.pan_min_angle_spin)
        
        self.pan_max_angle_spin = QSpinBox()
        self.pan_max_angle_spin.setMinimum(0)
        self.pan_max_angle_spin.setMaximum(180)
        servo_settings_form.addRow("Pan Max Açı:", self.pan_max_angle_spin)
        
        # Tilt min/max angle
        self.tilt_min_angle_spin = QSpinBox()
        self.tilt_min_angle_spin.setMinimum(-90)
        self.tilt_min_angle_spin.setMaximum(0)
        servo_settings_form.addRow("Tilt Min Açı:", self.tilt_min_angle_spin)
        
        self.tilt_max_angle_spin = QSpinBox()
        self.tilt_max_angle_spin.setMinimum(0)
        self.tilt_max_angle_spin.setMaximum(90)
        servo_settings_form.addRow("Tilt Max Açı:", self.tilt_max_angle_spin)
        
        # Add test button for servo center position
        test_center_button = QPushButton("Servo Merkez Noktasını Test Et")
        test_center_button.clicked.connect(self.test_servo_center)
        servo_settings_form.addRow("", test_center_button)
        
        # Add servo settings group to tab layout
        connection_layout.addWidget(servo_settings_group)
        
        # Add the tab to tab widget
        self.tab_widget.addTab(connection_tab, "Bağlantı")
    
    def create_system_tab(self):
        """Create the system settings tab."""
        system_tab = QWidget()
        system_layout = QVBoxLayout(system_tab)
        
        # Models group
        models_group = QGroupBox("Model Ayarları")
        models_form = QFormLayout(models_group)
        
        # Model directory
        self.model_dir_edit = QLineEdit()
        models_form.addRow("Model Dizini:", self.model_dir_edit)
        
        # Use GPU checkbox
        self.use_gpu_check = QCheckBox("GPU Kullan (CUDA)")
        models_form.addRow("", self.use_gpu_check)
        
        # Add models group to tab layout
        system_layout.addWidget(models_group)
        
        # Log and storage group
        log_group = QGroupBox("Log ve Depolama")
        log_form = QFormLayout(log_group)
        
        # Log directory
        self.log_dir_edit = QLineEdit()
        log_form.addRow("Log Dizini:", self.log_dir_edit)
        
        # Captures directory
        self.captures_dir_edit = QLineEdit()
        log_form.addRow("Kayıt Dizini:", self.captures_dir_edit)
        
        # Add log group to tab layout
        system_layout.addWidget(log_group)
        
        # Add the tab to tab widget
        self.tab_widget.addTab(system_tab, "Sistem")
    
    def populate_resolution_combo(self):
        """Populate the resolution combobox with available options."""
        # Standard resolutions
        resolutions = [
            "320x240",
            "640x480",
            "800x600",
            "1024x768",
            "1280x720",
            "1920x1080",
        ]
        
        # Add available resolutions
        self.camera_resolution_combo.clear()
        self.camera_resolution_combo.addItems(resolutions)
    
    def populate_serial_ports(self):
        """Populate the serial port combobox with available ports."""
        try:
            # Save current selection if any
            current_port = self.serial_port_combo.currentText() if self.serial_port_combo.count() > 0 else ""
            
            # Clear existing items
            self.serial_port_combo.clear()
            
            # Get available serial ports
            available_ports = []
            ports = list(serial.tools.list_ports.comports())
            
            for port in ports:
                available_ports.append(port.device)
                # Add port name and description
                self.serial_port_combo.addItem(f"{port.device} - {port.description}")
                
            # If no ports found, add a message
            if not available_ports:
                self.serial_port_combo.addItem("COM Portu Bulunamadı")
                self.logger.warning("Kullanılabilir COM portu bulunamadı")
            
            # Add manual entry option
            self.serial_port_combo.addItem("Manuel Giriş")
            
            # Try to restore previous selection
            if current_port:
                for i in range(self.serial_port_combo.count()):
                    if current_port in self.serial_port_combo.itemText(i):
                        self.serial_port_combo.setCurrentIndex(i)
                        break
                        
            # Connect to index changed signal to show/hide manual entry
            self.serial_port_combo.currentIndexChanged.connect(self.on_serial_port_changed)
            
            self.logger.info(f"{len(available_ports)} COM portu bulundu")
            
        except Exception as e:
            self.logger.error(f"COM portlarını listelerken hata: {str(e)}")
            self.serial_port_combo.clear()
            self.serial_port_combo.addItem("COM Portu Bulunamadı")
    
    def on_serial_port_changed(self, index):
        """Handle serial port combo box index change."""
        if self.serial_port_combo.currentText() == "Manuel Giriş":
            # Show manual entry dialog
            port, ok = QInputDialog.getText(self, "Manuel COM Port Girişi", 
                                          "COM Port Adı Girin (örn. COM8):",
                                          QLineEdit.Normal, "")
            if ok and port:
                # Add the port to combo and select it
                self.serial_port_combo.insertItem(0, port)
                self.serial_port_combo.setCurrentIndex(0)
            else:
                # If canceled, revert to first item or to the saved port
                if config.pan_tilt_serial_port and self.serial_port_combo.count() > 1:
                    for i in range(self.serial_port_combo.count()):
                        if config.pan_tilt_serial_port in self.serial_port_combo.itemText(i):
                            self.serial_port_combo.setCurrentIndex(i)
                            break
                    else:
                        self.serial_port_combo.setCurrentIndex(0)
                else:
                    self.serial_port_combo.setCurrentIndex(0)
    
    def load_settings(self):
        """Load current settings into UI components."""
        # Camera settings
        self.camera_id_spin.setValue(config.camera_id)
        
        # Get current camera resolution
        width, height = 640, 480  # Default values
        if hasattr(self.parent, 'camera_service') and self.parent.camera_service:
            try:
                width, height = self.parent.camera_service.get_frame_dimensions()
            except:
                pass
        current_resolution = f"{width}x{height}"
        
        # Set resolution in combobox
        index = self.camera_resolution_combo.findText(current_resolution)
        if index >= 0:
            self.camera_resolution_combo.setCurrentIndex(index)
        
        # FPS limit
        self.fps_limit_spin.setValue(config.camera_fps)
        
        # Save format - assume JPEG is default if not specified
        save_format = getattr(config, 'save_format', "JPEG")
        index = self.save_format_combo.findText(save_format)
        if index >= 0:
            self.save_format_combo.setCurrentIndex(index)
        
        # Connection settings
        self.serial_port_combo.clear()
        self.populate_serial_ports()
        
        # Find baud rate in combo
        baud_rate = str(config.pan_tilt_baud_rate)
        index = self.baud_rate_combo.findText(baud_rate)
        if index >= 0:
            self.baud_rate_combo.setCurrentIndex(index)
        
        # Servo center position settings
        self.pan_center_spin.setValue(getattr(config, 'pan_center', 90))
        self.tilt_center_spin.setValue(getattr(config, 'tilt_center', 90))
        
        # Servo angle settings - use defaults if not in config
        self.pan_min_angle_spin.setValue(getattr(config, 'pan_min_angle', -90))
        self.pan_max_angle_spin.setValue(getattr(config, 'pan_max_angle', 90))
        self.tilt_min_angle_spin.setValue(getattr(config, 'tilt_min_angle', -45))
        self.tilt_max_angle_spin.setValue(getattr(config, 'tilt_max_angle', 45))
        
        # System settings
        self.model_dir_edit.setText(config.model_dir)
        self.log_dir_edit.setText(config.logs_dir)
        self.captures_dir_edit.setText(config.captures_dir)
        self.use_gpu_check.setChecked(config.use_gpu)
        
        # Additional settings
        self.auto_exposure_check.setChecked(getattr(config, 'auto_exposure', True))
        self.auto_wb_check.setChecked(getattr(config, 'auto_white_balance', True))
    
    def apply_settings(self):
        """Apply the changed settings."""
        try:
            # Remember old values for camera
            old_camera_id = config.camera_id
            old_camera_fps = config.camera_fps
            old_camera_width = getattr(config, 'camera_width', 640)
            old_camera_height = getattr(config, 'camera_height', 480)
            
            # Update config with form values
            # Camera settings
            config.camera_id = self.camera_id_spin.value()
            config.camera_fps = self.fps_limit_spin.value()
            config.save_format = self.save_format_combo.currentText()
            
            # Get selected resolution
            resolution = self.camera_resolution_combo.currentText()
            width, height = map(int, resolution.split('x'))
            config.camera_width = width
            config.camera_height = height
            
            # Connection settings
            # Extract actual port name (COM1, COM2, etc.) from the selection string
            selected_port = self.serial_port_combo.currentText()
            if " - " in selected_port:  # Format is typically "COM1 - USB Serial Device"
                config.pan_tilt_serial_port = selected_port.split(" - ")[0]
            elif selected_port != "COM Portu Bulunamadı" and selected_port != "Manuel Giriş":
                config.pan_tilt_serial_port = selected_port
            
            config.pan_tilt_baud_rate = int(self.baud_rate_combo.currentText())
            
            # Servo center position settings
            config.pan_center = self.pan_center_spin.value()
            config.tilt_center = self.tilt_center_spin.value()
            
            # Servo angle settings
            config.pan_min_angle = self.pan_min_angle_spin.value()
            config.pan_max_angle = self.pan_max_angle_spin.value()
            config.tilt_min_angle = self.tilt_min_angle_spin.value()
            config.tilt_max_angle = self.tilt_max_angle_spin.value()
            
            # System settings
            config.model_dir = self.model_dir_edit.text()
            config.logs_dir = self.log_dir_edit.text()
            config.captures_dir = self.captures_dir_edit.text()
            config.use_gpu = self.use_gpu_check.isChecked()
            
            # Additional settings
            config.auto_exposure = self.auto_exposure_check.isChecked()
            config.auto_white_balance = self.auto_wb_check.isChecked()
            
            # Ensure directories exist
            config.ensure_dirs_exist()
            
            # Check if camera needs to be restarted
            restart_camera = (old_camera_id != config.camera_id or 
                            old_camera_fps != config.camera_fps)
            
            # Check if resolution changed
            resolution_changed = (old_camera_width != config.camera_width or
                                old_camera_height != config.camera_height)
            
            # Apply camera resolution changes
            if hasattr(self.parent, 'camera_service') and self.parent.camera_service:
                # If resolution changed, update it
                current_width, current_height = self.parent.camera_service.get_frame_dimensions()
                if resolution_changed or restart_camera:
                    # Ask user if they want to apply changes that require camera restart
                    reply = QMessageBox.question(
                        self, 
                        "Kamera Ayarları Değişikliği",
                        "Kamera ayarları değişikliği kameranın yeniden başlatılmasını gerektiriyor. Devam etmek istiyor musunuz?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        # Release current camera
                        self.parent.camera_service.release()
                        
                        # Re-initialize with new settings
                        if hasattr(self.parent, 'init_camera'):
                            self.parent.init_camera()
                            
                            # Update pan-tilt frame center if available and resolution changed
                            if resolution_changed and hasattr(self.parent, 'pan_tilt_service') and self.parent.pan_tilt_service:
                                self.parent.pan_tilt_service.set_frame_center(config.camera_width, config.camera_height)
                                self.logger.info(f"Pan-Tilt servisi kare merkezi güncellendi: {config.camera_width}x{config.camera_height}")
                    else:
                        # Revert to previous camera settings
                        config.camera_id = old_camera_id
                        config.camera_fps = old_camera_fps
                        config.camera_width = old_camera_width
                        config.camera_height = old_camera_height
            
            self.logger.info("Ayarlar başarıyla uygulandı")
            QMessageBox.information(self, "Ayarlar", "Ayarlar başarıyla uygulandı.")
            return True
            
        except Exception as e:
            self.logger.error(f"Ayarlar uygulanırken hata: {str(e)}")
            QMessageBox.critical(self, "Hata", f"Ayarlar uygulanırken hata oluştu: {str(e)}")
            return False
    
    def save_and_close(self):
        """Save settings and close the dialog."""
        if self.apply_settings():
            self.accept()
    
    def test_servo_center(self):
        """Test the servo center position by sending center command."""
        try:
            if hasattr(self.parent, 'pan_tilt_service') and self.parent.pan_tilt_service:
                # Get center positions from UI
                pan_center = self.pan_center_spin.value()
                tilt_center = self.tilt_center_spin.value()
                
                # Send center command
                self.parent.pan_tilt_service.send_command(f"P{pan_center}T{tilt_center}")
                self.logger.info(f"Test merkez komut gönderildi: P{pan_center}T{tilt_center}")
                
                QMessageBox.information(self, "Servo Test", f"Servo merkez pozisyonuna komut gönderildi: P{pan_center}T{tilt_center}")
            else:
                QMessageBox.warning(self, "Servo Test", "Pan-Tilt servisi aktif değil. Önce servo izleme modunu etkinleştirin.")
        except Exception as e:
            self.logger.error(f"Servo testi sırasında hata: {str(e)}")
            QMessageBox.critical(self, "Hata", f"Servo testi sırasında hata oluştu: {str(e)}") 