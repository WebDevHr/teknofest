#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Window
----------
Main window for the camera application.
"""

import sys
import os
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QPushButton, QMessageBox, QLabel
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QFont, QIcon, QColor
from datetime import datetime

from services.logger_service import LoggerService
from services.camera_service import CameraService
from services.balloon_detector_service import BalloonDetectorService
from services.friend_foe_service import FriendFoeService
from services.engagement_mode_service import EngagementModeService
from services.engagement_board_service import EngagementBoardService
from services.mock_service import MockService
from services.pan_tilt_service import PanTiltService
from ui.sidebar import LogSidebar, MenuSidebar, IconThemeManager
from ui.camera_view import CameraView
from ui.shape_dialog import ShapeDetectionDialog
from utils.config import config

class MainWindow(QMainWindow):
    """
    Main window for the camera application.
    Implements the Facade pattern to coordinate components.
    """
    
    def __init__(self):
        super().__init__()
        
        # Get logger service
        self.logger = LoggerService()
        
        # Set default theme
        self.current_theme = "dark"  # Default to dark theme
        
        # Initialize UI components
        self.init_ui()
        
        # Initialize camera service
        self.init_camera()
        
        # Initialize pan-tilt service
        self.init_pan_tilt_service()
        
        # Show the window in full screen mode instead of maximized
        self.showFullScreen()
        
        # Position the toggle buttons after showing the window
        self.update_toggle_button_positions()
        
        # Log that application has started
        self.logger.info("Uygulama tam ekran modunda başlatıldı")
        
        # Show initial log messages in the sidebar
        self.load_existing_logs()
        
    def init_ui(self):
        """Initialize the user interface components."""
        # Set window properties
        self.setWindowTitle("Modern Kamera Uygulaması")
        
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create camera view with stretch factor to maximize its space
        self.camera_view = CameraView()
        
        # Create left sidebar (Log Window) - start with 0 width
        self.log_sidebar = LogSidebar(self)
        self.log_sidebar.setFixedWidth(0)  # Start with zero width
        
        # Connect logger signals to log sidebar
        self.logger.log_added.connect(self.log_sidebar.add_log)
        
        # Create right sidebar (Menu) - start with 0 width
        self.menu_sidebar = MenuSidebar(self)
        self.menu_sidebar.setFixedWidth(0)  # Start with zero width
        
        # Connect menu button signals
        self.menu_sidebar.settings_button.clicked.connect(self.on_settings_clicked)
        self.menu_sidebar.save_button.clicked.connect(self.on_save_clicked)
        self.menu_sidebar.balloon_dl_button.clicked.connect(self.on_balloon_dl_clicked)
        self.menu_sidebar.balloon_edge_button.clicked.connect(self.on_balloon_edge_clicked)
        self.menu_sidebar.balloon_color_button.clicked.connect(self.on_balloon_color_clicked)
        self.menu_sidebar.balloon_classic_button.clicked.connect(self.on_balloon_classic_clicked)
        self.menu_sidebar.friend_foe_dl_button.clicked.connect(self.on_friend_foe_dl_clicked)
        self.menu_sidebar.friend_foe_classic_button.clicked.connect(self.on_friend_foe_classic_clicked)
        self.menu_sidebar.engagement_dl_button.clicked.connect(self.on_engagement_dl_clicked)
        self.menu_sidebar.engagement_hybrid_button.clicked.connect(self.on_engagement_hybrid_clicked)
        self.menu_sidebar.engagement_board_button.clicked.connect(self.on_engagement_board_clicked)
        self.menu_sidebar.theme_button.clicked.connect(self.toggle_theme)
        self.menu_sidebar.exit_button.clicked.connect(self.on_exit_clicked)
        self.menu_sidebar.emergency_stop_button.clicked.connect(self.on_emergency_stop_clicked)
        self.menu_sidebar.tracking_button.clicked.connect(self.on_tracking_clicked)
        self.menu_sidebar.servo_control_button.clicked.connect(self.on_servo_control_clicked)
        
        # Base directory for icons - use absolute path
        icon_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
        
        # Add fullscreen toggle button
        self.fullscreen_toggle_btn = QPushButton()
        self.fullscreen_toggle_btn.setFixedSize(40, 40)
        self.fullscreen_toggle_btn.clicked.connect(self.toggle_fullscreen)
        self.fullscreen_toggle_btn.setParent(self)
        
        # Load fullscreen icon if available
        fullscreen_icon_path = os.path.join(icon_base_dir, "fullscreen.png")
        if os.path.exists(fullscreen_icon_path):
            themed_icon = IconThemeManager.get_themed_icon(fullscreen_icon_path, is_dark_theme=self.current_theme == "dark")
            self.fullscreen_toggle_btn.setIcon(themed_icon)
            self.fullscreen_toggle_btn.setIconSize(QSize(24, 24))
        
        # Buton stillemesi
        self.fullscreen_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(231, 76, 60, 180);
                border-radius: 12px;
                padding: 1px;
                min-width: 40px;
                min-height: 40px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(231, 76, 60, 220);
            }
        """)
        self.fullscreen_toggle_btn.setToolTip("Tam Ekran Değiştir")
        
        # Add widgets to main layout with proper stretch factors
        self.main_layout.addWidget(self.log_sidebar, 0)  # No stretch
        self.main_layout.addWidget(self.camera_view, 1)  # Stretch to fill available space
        self.main_layout.addWidget(self.menu_sidebar, 0)  # No stretch
        
        # Create toggle buttons for sidebars with icons
        self.left_toggle_btn = QPushButton()
        self.left_toggle_btn.setFixedSize(40, 40)
        self.left_toggle_btn.clicked.connect(self.toggle_left_sidebar)
        
        # Load log icon if available
        self.log_icon_open_path = os.path.join(icon_base_dir, "log.png")  # Açık ikon
        self.log_icon_close_path = os.path.join(icon_base_dir, "arrow-left.png")  # Kapalı ikon
        
        # İlk icon'u yükle (kapalı durumu için)
        if os.path.exists(self.log_icon_open_path):
            themed_icon = IconThemeManager.get_themed_icon(self.log_icon_open_path, is_dark_theme=self.current_theme == "dark")
            self.left_toggle_btn.setIcon(themed_icon)
            self.left_toggle_btn.setIconSize(QSize(20, 20))
        
        # Buton stillemesi
        self.left_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(76, 175, 80, 180);
                border-radius: 12px;
                padding: 1px;
                min-width: 40px;
                min-height: 40px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(76, 175, 80, 220);
            }
        """)
        self.left_toggle_btn.setToolTip("Log Panelini Aç/Kapat")
        
        self.right_toggle_btn = QPushButton()
        self.right_toggle_btn.setFixedSize(40, 40)
        self.right_toggle_btn.clicked.connect(self.toggle_right_sidebar)
        
        # Load menu icon if available
        self.menu_icon_open_path = os.path.join(icon_base_dir, "menu.png")  # Açık ikon
        self.menu_icon_close_path = os.path.join(icon_base_dir, "arrow-right.png")  # Kapalı ikon
        
        # İlk icon'u yükle (kapalı durumu için)
        if os.path.exists(self.menu_icon_open_path):
            themed_icon = IconThemeManager.get_themed_icon(self.menu_icon_open_path, is_dark_theme=self.current_theme == "dark")
            self.right_toggle_btn.setIcon(themed_icon)
            self.right_toggle_btn.setIconSize(QSize(20, 20))
        
        # Buton stillemesi
        self.right_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(33, 150, 243, 180);
                border-radius: 12px;
                padding: 1px;
                min-width: 40px;
                min-height: 40px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 220);
            }
        """)
        self.right_toggle_btn.setToolTip("Menü Panelini Aç/Kapat")
        
        # Position toggle buttons
        self.left_toggle_btn.setParent(self)
        self.right_toggle_btn.setParent(self)
        
        # Connect sidebar animation signals
        self.log_sidebar.animation_value_changed.connect(self.update_toggle_button_positions)
        self.menu_sidebar.animation_value_changed.connect(self.update_toggle_button_positions)
        
        # Create FPS display label before apply_theme is called indirectly by create_sidebar_toggles
        self.init_fps_display()
        
        # Apply the default theme
        self.apply_theme()
    
    def apply_theme(self):
        """Apply the current theme to the application."""
        if self.current_theme == "dark":
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
            
    def apply_dark_theme(self):
        """Apply dark theme (night mode)."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                background-color: #121212;
                color: white;
            }
            QPushButton {
                background-color: #333333;
                color: white;
                border-radius: 5px;
                padding: 5px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #555555;
            }
            QPushButton#theme_button {
                text-align: left;
                padding-left: 40px;
            }
        """)
        
        # Set the camera view background color
        self.camera_view.setStyleSheet("background-color: #2E2E2E;")
        
        # Set sidebar backgrounds
        self.log_sidebar.setStyleSheet("background-color: #333333;")
        self.menu_sidebar.setStyleSheet("background-color: #333333;")
        
        # Update FPS label style
        self.update_fps_label_style()
        
        # Update the text area style if method exists
        if hasattr(self.log_sidebar, 'update_text_area_style'):
            self.log_sidebar.update_text_area_style(is_dark=True)
        
        # Update the sidebar theme if the method exists
        if hasattr(self.menu_sidebar, 'update_theme'):
            self.menu_sidebar.update_theme(is_dark=True)
        else:
            self.menu_sidebar.theme_button.setText("Açık Tema")
        
        # Base directory for icons - use absolute path
        icon_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
        
        # Update toggle buttons
        self.left_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(76, 175, 80, 180);
                border-radius: 12px;
                padding: 1px;
                border: 1px solid #2E7D32;
                min-width: 40px;
                min-height: 40px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(76, 175, 80, 220);
            }
        """)
        
        # Update left toggle button icon based on current state
        if self.log_sidebar.is_open:
            if os.path.exists(self.log_icon_close_path):
                themed_icon = IconThemeManager.get_themed_icon(self.log_icon_close_path, is_dark_theme=True)
                self.left_toggle_btn.setIcon(themed_icon)
        else:
            if os.path.exists(self.log_icon_open_path):
                themed_icon = IconThemeManager.get_themed_icon(self.log_icon_open_path, is_dark_theme=True)
                self.left_toggle_btn.setIcon(themed_icon)
        
        self.right_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(33, 150, 243, 180);
                border-radius: 12px;
                padding: 1px;
                border: 1px solid #1565C0;
                min-width: 40px;
                min-height: 40px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 220);
            }
        """)
        
        # Update right toggle button icon based on current state
        if self.menu_sidebar.is_open:
            if os.path.exists(self.menu_icon_close_path):
                themed_icon = IconThemeManager.get_themed_icon(self.menu_icon_close_path, is_dark_theme=True)
                self.right_toggle_btn.setIcon(themed_icon)
        else:
            if os.path.exists(self.menu_icon_open_path):
                themed_icon = IconThemeManager.get_themed_icon(self.menu_icon_open_path, is_dark_theme=True)
                self.right_toggle_btn.setIcon(themed_icon)
        
        # Update fullscreen toggle button
        self.fullscreen_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(231, 76, 60, 180);
                border-radius: 12px;
                padding: 1px;
                border: 1px solid #C0392B;
                min-width: 40px;
                min-height: 40px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(231, 76, 60, 220);
            }
        """)
        
        # Log theme change
        self.logger.info("Koyu temaya geçildi")
        
        self.current_theme = "dark"
    
    def apply_light_theme(self):
        """Apply light theme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QWidget {
                background-color: #f0f0f0;
                color: black;
            }
            QPushButton {
                background-color: #e0e0e0;
                color: black;
                border-radius: 5px;
                padding: 5px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QPushButton#theme_button {
                text-align: left;
                padding-left: 40px;
            }
        """)
        
        # Set the camera view background color
        self.camera_view.setStyleSheet("background-color: #F5F5F5;")
        
        # Set sidebar backgrounds
        self.log_sidebar.setStyleSheet("background-color: #E0E0E0;")
        self.menu_sidebar.setStyleSheet("background-color: #E0E0E0;")
        
        # Update FPS label style
        self.update_fps_label_style()
        
        # Update the text area style if method exists
        if hasattr(self.log_sidebar, 'update_text_area_style'):
            self.log_sidebar.update_text_area_style(is_dark=False)
        
        # Update the sidebar theme if the method exists
        if hasattr(self.menu_sidebar, 'update_theme'):
            self.menu_sidebar.update_theme(is_dark=False)
        else:
            self.menu_sidebar.theme_button.setText("Koyu Tema")
        
        # Base directory for icons - use absolute path
        icon_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
        
        # Update toggle buttons
        self.left_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(76, 175, 80, 220);
                border-radius: 12px;
                padding: 1px;
                border: 1px solid #2E7D32;
                min-width: 40px;
                min-height: 40px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(76, 175, 80, 255);
            }
        """)
        
        # Update left toggle button icon based on current state
        if self.log_sidebar.is_open:
            if os.path.exists(self.log_icon_close_path):
                themed_icon = IconThemeManager.get_themed_icon(self.log_icon_close_path, is_dark_theme=False)
                self.left_toggle_btn.setIcon(themed_icon)
        else:
            if os.path.exists(self.log_icon_open_path):
                themed_icon = IconThemeManager.get_themed_icon(self.log_icon_open_path, is_dark_theme=False)
                self.left_toggle_btn.setIcon(themed_icon)
        
        self.right_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(33, 150, 243, 220);
                border-radius: 12px;
                padding: 1px;
                border: 1px solid #1565C0;
                min-width: 40px;
                min-height: 40px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 255);
            }
        """)
        
        # Update right toggle button icon based on current state
        if self.menu_sidebar.is_open:
            if os.path.exists(self.menu_icon_close_path):
                themed_icon = IconThemeManager.get_themed_icon(self.menu_icon_close_path, is_dark_theme=False)
                self.right_toggle_btn.setIcon(themed_icon)
        else:
            if os.path.exists(self.menu_icon_open_path):
                themed_icon = IconThemeManager.get_themed_icon(self.menu_icon_open_path, is_dark_theme=False)
                self.right_toggle_btn.setIcon(themed_icon)
        
        # Update fullscreen toggle button
        self.fullscreen_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(231, 76, 60, 220);
                border-radius: 12px;
                padding: 1px;
                border: 1px solid #C0392B;
                min-width: 40px;
                min-height: 40px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(231, 76, 60, 255);
            }
        """)
        
        # Log theme change
        self.logger.info("Açık temaya geçildi")
        
        self.current_theme = "light"
    
    def toggle_theme(self):
        """Toggle between dark and light themes."""
        if self.current_theme == "dark":
            self.current_theme = "light"
        else:
            self.current_theme = "dark"
        
        # Apply the new theme
        self.apply_theme()
    
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
            
        # Daha yüksek FPS ile kamerayı başlat (30 FPS)
        self.camera_service.start(fps=30)
    
    def on_camera_error(self, error_message):
        """Handle camera errors."""
        self.logger.error(f"Kamera hatası: {error_message}")
        QMessageBox.critical(self, "Kamera Hatası", error_message)
    
    def toggle_left_sidebar(self):
        """Toggle the visibility of the left sidebar."""
        is_open = self.log_sidebar.toggle()
        
        # Update button tooltip and icon based on current state
        if is_open:
            self.left_toggle_btn.setToolTip("Logları Gizle")
            # Log sidebar açık, kapatma ikonu göster
            if os.path.exists(self.log_icon_close_path):
                themed_icon = IconThemeManager.get_themed_icon(self.log_icon_close_path, is_dark_theme=self.current_theme == "dark")
                self.left_toggle_btn.setIcon(themed_icon)
        else:
            self.left_toggle_btn.setToolTip("Logları Göster")
            # Log sidebar kapalı, açma ikonu göster
            if os.path.exists(self.log_icon_open_path):
                themed_icon = IconThemeManager.get_themed_icon(self.log_icon_open_path, is_dark_theme=self.current_theme == "dark")
                self.left_toggle_btn.setIcon(themed_icon)
            
        # When the sidebar is opened, make sure it gets updated with all logs
        if is_open:
            # Refresh logs in sidebar for better visibility
            self.refresh_log_sidebar()
    
    def refresh_log_sidebar(self):
        """Refresh the log sidebar with all logs."""
        # Get all logs from the logger service
        all_logs = self.logger.get_logs()
        
        # Clear existing logs in the sidebar to avoid duplicates
        self.log_sidebar.clear_logs()
        
        # Add all logs to the sidebar
        for log in all_logs:
            self.log_sidebar.add_log(log)
            
        # Force the sidebar to update
        self.log_sidebar.update()
    
    def toggle_right_sidebar(self):
        """Toggle the visibility of the right sidebar."""
        is_open = self.menu_sidebar.toggle()
        
        # Update button tooltip and icon based on current state
        if is_open:
            self.right_toggle_btn.setToolTip("Menüyü Gizle")
            # Menu sidebar açık, kapatma ikonu göster
            if os.path.exists(self.menu_icon_close_path):
                themed_icon = IconThemeManager.get_themed_icon(self.menu_icon_close_path, is_dark_theme=self.current_theme == "dark")
                self.right_toggle_btn.setIcon(themed_icon)
        else:
            self.right_toggle_btn.setToolTip("Menüyü Göster")
            # Menu sidebar kapalı, açma ikonu göster
            if os.path.exists(self.menu_icon_open_path):
                themed_icon = IconThemeManager.get_themed_icon(self.menu_icon_open_path, is_dark_theme=self.current_theme == "dark")
                self.right_toggle_btn.setIcon(themed_icon)
    
    def update_toggle_button_positions(self):
        """Update the positions of the toggle buttons."""
        # Position left toggle button
        left_x = self.log_sidebar.width() + 15
        self.left_toggle_btn.move(left_x, 15)
        
        # Position right toggle button
        right_x = self.width() - self.menu_sidebar.width() - self.right_toggle_btn.width() - 15
        self.right_toggle_btn.move(right_x, 15)
        
        # Position fullscreen toggle button in the top center
        fullscreen_x = (self.width() - self.fullscreen_toggle_btn.width()) // 2
        self.fullscreen_toggle_btn.move(fullscreen_x, 15)
    
    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        
        # Update toggle button positions
        self.update_toggle_button_positions()
        
        # CameraView'da update_size metodu olmadığı için kaldırıldı
        # Gerekirse burada kamera görünümü için farklı bir güncelleme yapılabilir
    
    def on_clear_log(self):
        """Handle Clear Log button click."""
        # Önce logger servisinden logları temizle
        # Bu "Logs cleared" mesajını da logları ekleyecek
        self.logger.clear()
        
        # Sonra log sidebar'daki tüm logları yenile
        self.refresh_log_sidebar()
    
    def on_settings_clicked(self):
        """Handle Settings button click."""
        # Ayarlar iletişim kutusunu göster
        settings_dialog = QMessageBox(self)
        settings_dialog.setWindowTitle("Ayarlar")
        settings_dialog.setIcon(QMessageBox.Information)
        settings_dialog.setText("Kamera Ayarları")
        
        # Ayarlar bilgisi
        settings_info = (
            "Kamera Çözünürlüğü: 1280x720\n"
            "FPS Limiti: 30\n"
            "Kayıt Formatı: JPEG\n"
            "Log Seviyesi: BİLGİ\n"
        )
        settings_dialog.setInformativeText(settings_info)
        
        # Butonlar
        settings_dialog.setStandardButtons(QMessageBox.Ok)
        settings_dialog.button(QMessageBox.Ok).setText("Kapat")
        
        # Log
        self.logger.info("Ayarlar iletişim kutusu görüntülendi")
        
        # İletişim kutusunu göster
        settings_dialog.exec_()
    
    def on_save_clicked(self):
        """Handle save button click."""
        # Save the current frame
        # Get the captures directory from config
        directory = config.captures_dir
            
        # Create directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(directory, f"capture_{timestamp}.png")
        
        # Save the frame
        success = self.camera_service.save_current_frame(filename)
        
        if success:
            self.logger.info(f"Görüntü {filename} olarak kaydedildi")
            
            # Show success message with the path
            QMessageBox.information(
                self,
                "Görüntü Kaydedildi",
                f"Görüntü başarıyla kaydedildi:\n{filename}"
            )
        else:
            self.logger.error("Görüntü kaydedilemedi")
            
            # Show error message
            QMessageBox.critical(
                self,
                "Kayıt Hatası",
                "Görüntü kaydedilemedi."
            )
    
    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Release camera resources
            if hasattr(self, 'camera_service'):
                self.camera_service.release()
            
            # Stop any active detector services
            self._stop_all_detection_services()
            
            # Release pan-tilt service resources
            if hasattr(self, 'pan_tilt_service') and self.pan_tilt_service:
                self.pan_tilt_service.release()
            
            # Accept the close event
            event.accept()
            self.logger.info("Uygulama kapatıldı")
        except Exception as e:
            self.logger.error(f"Uygulama kapatılırken hata oluştu: {str(e)}")
            event.accept()  # Still close the application
    
    def init_fps_display(self):
        """Initialize the FPS display label."""
        # Style the FPS label in the sidebar based on current theme
        if hasattr(self, 'menu_sidebar'):
            self.update_fps_label_style()
        
        # Create timer to update the FPS
        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(200)  # Daha sık güncelleme - 200 ms (saniyede 5 güncelleme)
    
    def update_fps(self):
        """Update the FPS display."""
        if hasattr(self, 'camera_service') and hasattr(self, 'menu_sidebar'):
            fps = self.camera_service.fps
            self.menu_sidebar.fps_label.setText(f"{fps:.1f}")
    
    def update_fps_label_style(self):
        """Update the FPS label style based on current theme."""
        if hasattr(self, 'menu_sidebar'):
            if self.current_theme == "dark":
                self.menu_sidebar.fps_label.setStyleSheet("""
                    background-color: #444444;
                    color: #4CAF50;
                    border-radius: 18px;
                    padding: 5px;
                    min-width: 36px;
                    min-height: 36px;
                    max-width: 36px;
                    max-height: 36px;
                    font-weight: bold;
                """)
            else:
                self.menu_sidebar.fps_label.setStyleSheet("""
                    background-color: #e0e0e0;
                    color: #2E7D32;
                    border-radius: 18px;
                    padding: 5px;
                    min-width: 36px;
                    min-height: 36px;
                    max-width: 36px;
                    max-height: 36px;
                    font-weight: bold;
                """)

    def on_exit_clicked(self):
        """Handle exit button click with confirmation dialog."""
        # Çıkış için onay iste
        confirm_dialog = QMessageBox(self)
        confirm_dialog.setWindowTitle("Çıkışı Onayla")
        confirm_dialog.setIcon(QMessageBox.Question)
        confirm_dialog.setText("Çıkmak istediğinize emin misiniz?")
        confirm_dialog.setInformativeText("Kaydedilmemiş veriler kaybolacaktır.")
        confirm_dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm_dialog.button(QMessageBox.Yes).setText("Evet, Çık")
        confirm_dialog.button(QMessageBox.No).setText("İptal")
        
        # Varsayılan butonu Hayır olarak ayarla (kullanıcı yanlışlıkla Enter'a basarsa)
        confirm_dialog.setDefaultButton(QMessageBox.No)
        
        # Yanıtı al
        response = confirm_dialog.exec_()
        
        # Eğer Evet dediyse çık
        if response == QMessageBox.Yes:
            self.logger.info("Kullanıcı çıkışı onayladı")
            self.close()
        else:
            self.logger.info("Çıkış kullanıcı tarafından iptal edildi")

    def on_emergency_stop_clicked(self):
        """Handle emergency stop button click."""
        self.logger.info("ACİL STOP: Tüm işlemler durduruldu")
        
        # Stop camera
        if hasattr(self, 'camera_service') and self.camera_service:
            self.camera_service.stop()
            self.logger.info("Kamera durduruldu")
            
        # Reset all detection buttons to unchecked state
        self.menu_sidebar.balloon_dl_button.setChecked(False)
        self.menu_sidebar.balloon_classic_button.setChecked(False)
        self.menu_sidebar.friend_foe_dl_button.setChecked(False)
        self.menu_sidebar.friend_foe_classic_button.setChecked(False)
        self.menu_sidebar.engagement_dl_button.setChecked(False)
        self.menu_sidebar.engagement_hybrid_button.setChecked(False)
        
        # Stop all detection services
        self._stop_all_detection_services()
            
        # Disable all active detections
        self.camera_view.set_detection_active(False)
        
        # Set warning message on camera view
        self.camera_view.show_message("ACİL STOP ETKİN!", QColor(255, 0, 0), 5000)
        
        # Update view with static image or warning screen
        self.camera_view.show_emergency_stop()
        
        # Update UI state
        self.emergency_mode = True
        
        # Show restart instruction
        QMessageBox.warning(self, "ACİL STOP", 
                          "Tüm işlemler durduruldu.\nYeniden başlatmak için uygulamayı kapatıp tekrar açın.")

    def _stop_all_detection_services(self):
        """Stop all active detection services."""
        # Stop balloon detector if active
        if hasattr(self, 'balloon_detector') and self.balloon_detector:
            self.balloon_detector.stop()
            self.logger.info("Balon dedektör servisi durduruldu")
            # Tamamen kaldır
            delattr(self, 'balloon_detector')
            
        # Stop friend/foe detector if active
        if hasattr(self, 'friend_foe_detector') and self.friend_foe_detector:
            self.friend_foe_detector.stop()
            self.logger.info("Dost/Düşman dedektör servisi durduruldu")
            
        # Stop engagement detector if active
        if hasattr(self, 'engagement_detector') and self.engagement_detector:
            self.engagement_detector.stop()
            self.logger.info("Angajman dedektör servisi durduruldu")
            
        # Stop engagement board detector if active
        if hasattr(self, 'engagement_board_detector') and self.engagement_board_detector:
            self.engagement_board_detector.stop()
            self.logger.info("Angajman tahtası dedektör servisi durduruldu")
            
        # Stop mock service if active
        if hasattr(self, 'mock_detector') and self.mock_detector:
            self.mock_detector.stop()
            self.logger.info("Mock dedektör servisi durduruldu")

    def on_balloon_dl_clicked(self):
        """Handle balloon detection with deep learning button click."""
        is_active = self.menu_sidebar.balloon_dl_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.balloon_dl_button)
            
            # Stop other active services
            self._stop_all_detection_services()
        
        # This uses the balloon detector service
        if is_active:
            self.logger.info("Hareketli Balon Modu (Derin Öğrenmeli + ByteTrack) aktif edildi")
            
            # Yeniden başlatmaya hazırlanıyor - özel modeli kullanacağız
            self.init_yolo()  # Initialize balloon detector with fresh instance
            self.camera_view.set_detection_active(True)
            self.camera_view.set_detection_mode("balloon")
        else:
            self.logger.info("Hareketli Balon Modu (Derin Öğrenmeli) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)
            # Stop services
            self._stop_all_detection_services()

    def on_balloon_classic_clicked(self):
        """Handle balloon detection with classical methods button click."""
        is_active = self.menu_sidebar.balloon_classic_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.balloon_classic_button)
            
            # Stop other active services
            self._stop_all_detection_services()
            
        if is_active:
            self.logger.info("Hareketli Balon Modu (Klasik Yöntemler) aktif edildi")
            self.balloon_classic_mock = self.init_mock_service("Balon Klasik Yöntemler")
            self.camera_view.set_detection_active(True)
            self.camera_view.set_detection_mode("balloon_classic")
        else:
            self.logger.info("Hareketli Balon Modu (Klasik Yöntemler) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)
            if hasattr(self, 'balloon_classic_mock') and self.balloon_classic_mock:
                self.balloon_classic_mock.stop()

    def on_friend_foe_dl_clicked(self):
        """Handle friend/foe detection with deep learning button click."""
        is_active = self.menu_sidebar.friend_foe_dl_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.friend_foe_dl_button)
            
            # Stop other active services
            self._stop_all_detection_services()
            
        if is_active:
            self.logger.info("Hareketli Dost/Düşman Modu (Derin Öğrenmeli) aktif edildi - friend_foe(v8n).pt modeli kullanılıyor")
            self.init_friend_foe_detector()  # Initialize Friend/Foe detector if needed
            self.camera_view.set_detection_active(True)
            self.camera_view.set_detection_mode("friend_foe")
        else:
            self.logger.info("Hareketli Dost/Düşman Modu (Derin Öğrenmeli) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)
            # Stop the service if it exists
            if hasattr(self, 'friend_foe_detector') and self.friend_foe_detector:
                self.friend_foe_detector.stop()

    def on_friend_foe_classic_clicked(self):
        """Handle friend/foe detection with classical methods button click."""
        is_active = self.menu_sidebar.friend_foe_classic_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.friend_foe_classic_button)
            
            # Stop other active services
            self._stop_all_detection_services()
            
        if is_active:
            self.logger.info("Hareketli Dost/Düşman Modu (Klasik Yöntemler) aktif edildi")
            self.friend_foe_classic_mock = self.init_mock_service("Dost/Düşman Klasik Yöntemler")
            self.camera_view.set_detection_active(True)
            self.camera_view.set_detection_mode("friend_foe_classic")
        else:
            self.logger.info("Hareketli Dost/Düşman Modu (Klasik Yöntemler) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)
            if hasattr(self, 'friend_foe_classic_mock') and self.friend_foe_classic_mock:
                self.friend_foe_classic_mock.stop()

    def on_engagement_hybrid_clicked(self):
        """Handle engagement detection with hybrid methods button click."""
        is_active = self.menu_sidebar.engagement_hybrid_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.engagement_hybrid_button)
            
            # Stop other active services
            self._stop_all_detection_services()
            
        if is_active:
            self.logger.info("Angajman Modu (Hibrit) aktif edildi")
            self.engagement_hybrid_mock = self.init_mock_service("Angajman Hibrit Yöntemler")
            self.camera_view.set_detection_active(True)
            self.camera_view.set_detection_mode("engagement_hybrid")
        else:
            self.logger.info("Angajman Modu (Hibrit) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)
            if hasattr(self, 'engagement_hybrid_mock') and self.engagement_hybrid_mock:
                self.engagement_hybrid_mock.stop()

    def _uncheck_other_detection_buttons(self, current_button):
        """Uncheck other detection mode buttons when one is checked."""
        # Dictionary of all detection buttons
        buttons = {
            self.menu_sidebar.balloon_dl_button,
            self.menu_sidebar.balloon_classic_button,
            self.menu_sidebar.friend_foe_dl_button,
            self.menu_sidebar.friend_foe_classic_button,
            self.menu_sidebar.engagement_dl_button,
            self.menu_sidebar.engagement_hybrid_button,
            self.menu_sidebar.engagement_board_button
        }
        
        # Uncheck all buttons except the current one
        for button in buttons:
            if button != current_button and button.isChecked():
                button.setChecked(False)

    def toggle_fullscreen(self):
        """Toggle between full screen and windowed mode."""
        # Base directory for icons - use absolute path
        icon_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
        
        if self.isFullScreen():
            self.showNormal()
            # Update tooltip
            self.fullscreen_toggle_btn.setToolTip("Tam Ekrana Geç")
            # Update icon to 'maximize' when in windowed mode
            fullscreen_icon_path = os.path.join(icon_base_dir, "fullscreen.png")
            if os.path.exists(fullscreen_icon_path):
                themed_icon = IconThemeManager.get_themed_icon(fullscreen_icon_path, is_dark_theme=self.current_theme == "dark")
                self.fullscreen_toggle_btn.setIcon(themed_icon)
            self.logger.info("Tam ekran modundan çıkıldı")
        else:
            self.showFullScreen()
            # Update tooltip
            self.fullscreen_toggle_btn.setToolTip("Tam Ekrandan Çık")
            # Update icon to 'minimize' when in fullscreen mode
            minimize_icon_path = os.path.join(icon_base_dir, "minimize.png")
            if os.path.exists(minimize_icon_path):
                themed_icon = IconThemeManager.get_themed_icon(minimize_icon_path, is_dark_theme=self.current_theme == "dark")
                self.fullscreen_toggle_btn.setIcon(themed_icon)
            elif os.path.exists(os.path.join(icon_base_dir, "fullscreen.png")):  # Fallback
                themed_icon = IconThemeManager.get_themed_icon(os.path.join(icon_base_dir, "fullscreen.png"), is_dark_theme=self.current_theme == "dark") 
                self.fullscreen_toggle_btn.setIcon(themed_icon)
            self.logger.info("Tam ekran moduna geçildi")
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        # Exit full screen when Escape key is pressed
        if event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.toggle_fullscreen()
            else:
                # Let the parent handle the escape key if not in full screen
                super().keyPressEvent(event)
        else:
            # Let the parent handle other keys
            super().keyPressEvent(event)
    
    def init_yolo(self):
        """Initialize the YOLO service for balloon tracking."""
        if not hasattr(self, 'balloon_detector') or not self.balloon_detector:
            # Create balloon detector service
            # Özel model dosyasını belirt
            model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "bestv8m_100_640.pt")
            self.balloon_detector = BalloonDetectorService(model_path=model_path)
            
            # Connect to camera service
            if hasattr(self, 'camera_service') and self.camera_service:
                self.camera_service.set_detector_service(self.balloon_detector)
            
            # Initialize service
            if not self.balloon_detector.initialize():
                self.logger.error("Failed to initialize Balloon detector service")
                return
            
            # Configure Kalman filter settings
            self.balloon_detector.use_kalman = True
            self.balloon_detector.show_kalman_debug = True
            
            self.logger.info(f"Balon dedektör servisi ve Kalman filtresi başlatıldı (Model: bestv8m_100_640.pt)")
            
        # Start service
        self.balloon_detector.start()

    def init_friend_foe_detector(self):
        """Initialize the service for friend/foe detection using the friend_foe(v8n).pt model."""
        if not hasattr(self, 'friend_foe_detector') or not self.friend_foe_detector:
            # Create friend/foe detector service
            self.friend_foe_detector = FriendFoeService()
            
            # Connect to camera service
            if hasattr(self, 'camera_service') and self.camera_service:
                self.camera_service.set_detector_service(self.friend_foe_detector)
            
            # Initialize service
            if not self.friend_foe_detector.initialize():
                self.logger.error("Failed to initialize Friend/Foe detector service")
                return
            
            self.logger.info("Dost/Düşman dedektör servisi başlatıldı - 2 sınıf: dost, dusman")
            
        # Start service
        self.friend_foe_detector.start()
    
    def init_engagement_detector(self, target_class=None):
        """Initialize the service for engagement mode using the engagement-best.pt model."""
        if not hasattr(self, 'engagement_detector') or not self.engagement_detector:
            # Create engagement detector service
            self.engagement_detector = EngagementModeService()
            
            # Connect to camera service
            if hasattr(self, 'camera_service') and self.camera_service:
                self.camera_service.set_detector_service(self.engagement_detector)
            
            # Initialize service
            if not self.engagement_detector.initialize():
                self.logger.error("Failed to initialize Engagement detector service")
                return
            
            self.logger.info("Angajman dedektör servisi başlatıldı - 9 sınıf: red-circle, red-square, red-triangle, blue-circle, blue-square, blue-triangle, green-circle, green-square, green-triangle")
            
        # Hedef sınıfı ayarla (belirtilmişse)
        if target_class is not None:
            self.engagement_detector.set_target_class(target_class)
            
        # Start service
        self.engagement_detector.start()

    def init_mock_service(self, name):
        """Initialize a mock service for non-implemented methods."""
        mock_service = MockService(service_name=name)
        
        # Connect to camera service
        if hasattr(self, 'camera_service') and self.camera_service:
            self.camera_service.set_detector_service(mock_service)
        
        mock_service.initialize()
        mock_service.start()
        return mock_service

    def on_engagement_dl_clicked(self):
        """Handle engagement detection with deep learning button click."""
        is_active = self.menu_sidebar.engagement_dl_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.engagement_dl_button)
            
            # Stop other active services
            self._stop_all_detection_services()
        
        # This uses the engagement detector service
        if is_active:
            self.logger.info("Hareketli Angajman Modu (Derin Öğrenmeli) aktif edildi")
            self.init_engagement_detector()  # Initialize Engagement detector if needed
            self.camera_view.set_detection_active(True)
            self.camera_view.set_detection_mode("engagement")
        else:
            self.logger.info("Hareketli Angajman Modu (Derin Öğrenmeli) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)
            # Stop the service if it exists
            if hasattr(self, 'engagement_detector') and self.engagement_detector:
                self.engagement_detector.stop()

    def load_existing_logs(self):
        """Load existing logs from the logger service to the sidebar."""
        # Clear previous logs first to avoid duplicates
        self.log_sidebar.clear_logs()
        
        # Get all existing logs
        existing_logs = self.logger.get_logs()
        
        # Add each log to the sidebar
        for log in existing_logs:
            self.log_sidebar.add_log(log)
        
        # Keep the log sidebar closed initially - don't force it open
        # We'll make sure it's in closed state
        self.log_sidebar.is_open = False
        
        # Set camera view to fill mode
        self.camera_view.set_scale_mode("fill")
        
        # Log Display Initialized
        self.logger.info("Log gösterimi başlatıldı")
                
    def on_tracking_clicked(self):
        """Handle tracking button click."""
        is_active = self.menu_sidebar.tracking_button.isChecked()
        
        if is_active:
            # Connect to Arduino
            if not hasattr(self, 'pan_tilt_service') or not self.pan_tilt_service:
                self.init_pan_tilt_service()
                
            # Connect to Arduino
            success = self.pan_tilt_service.connect()
            if not success:
                # If connection failed, uncheck the button
                self.menu_sidebar.tracking_button.setChecked(False)
                QMessageBox.critical(self, "Bağlantı Hatası", 
                                   "Pan-Tilt servoları ile bağlantı kurulamadı. COM8 bağlantı noktasını ve Arduino'nun bağlı olduğunu kontrol edin.")
                return
                
            # Connect the pan_tilt service to the balloon detector if available
            if hasattr(self, 'balloon_detector') and self.balloon_detector:
                self.pan_tilt_service.set_balloon_detector(self.balloon_detector)
                
                # Update frame dimensions
                if hasattr(self, 'camera_service') and self.camera_service:
                    width, height = self.camera_service.get_frame_dimensions()
                    self.pan_tilt_service.set_frame_center(width, height)
                
                # Start tracking
                self.pan_tilt_service.start_tracking()
                self.logger.info("Balon takibi başlatıldı")
                
            else:
                # No balloon detector available, show error
                self.menu_sidebar.tracking_button.setChecked(False)
                QMessageBox.warning(self, "Takip Hatası", 
                                   "Takip için balon dedektörü aktif değil. Önce 'Hareketli Balon Modu (Derin Öğrenmeli)' modunu etkinleştirin.")
        else:
            # Stop tracking
            if hasattr(self, 'pan_tilt_service') and self.pan_tilt_service:
                self.pan_tilt_service.stop_tracking()
                self.logger.info("Balon takibi durduruldu")

    def init_pan_tilt_service(self):
        """Initialize the PanTiltService."""
        self.pan_tilt_service = PanTiltService()
        
        # Connect the pan_tilt_service to the camera_service for visualization
        if hasattr(self, 'camera_service') and self.camera_service:
            self.camera_service.set_pan_tilt_service(self.pan_tilt_service)
            # Update frame dimensions
            width, height = self.camera_service.get_frame_dimensions()
            self.pan_tilt_service.set_frame_center(width, height)
            
        self.logger.info("PanTilt servisi başlatıldı (Gelişmiş IBVS ile)")

    def on_engagement_board_clicked(self):
        """Handle engagement board button click."""
        is_active = self.menu_sidebar.engagement_board_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.engagement_board_button)
            
            # Stop other active services
            self._stop_all_detection_services()
        
        # This uses the engagement board detector service with OCR
        if is_active:
            self.logger.info("Angajman Tahtası Okuması modu aktif edildi - YOLO ve OCR kullanılıyor")
            self.init_engagement_board_detector()  # Initialize Engagement board detector
            
            # Set detection mode for camera view
            if hasattr(self, 'camera_service') and self.camera_service:
                self.camera_view.set_detection_active(True)
                self.camera_view.set_detection_mode("engagement_board")
                self.logger.info("Tek kare yakalama ve analiz modu aktif - karakter ve şekil tespit edildiğinde duracak")
            else:
                self.logger.error("Kamera servisi bulunamadı")
        else:
            self.logger.info("Angajman Tahtası Okuması modu devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)
            # Stop the service if it exists
            if hasattr(self, 'engagement_board_detector') and self.engagement_board_detector:
                self.engagement_board_detector.stop()
                
    def init_engagement_board_detector(self):
        """Initialize the service for engagement board detection using YOLO and OCR."""
        if not hasattr(self, 'engagement_board_detector') or not self.engagement_board_detector:
            # Create engagement board detector service
            self.engagement_board_detector = EngagementBoardService()
            
            # Tespit tamamlandığında engagement mode'a geç
            self.engagement_board_detector.detection_completed.connect(self.switch_to_engagement_mode)
            
            # Connect to camera service
            if hasattr(self, 'camera_service') and self.camera_service:
                self.camera_service.set_detector_service(self.engagement_board_detector)
            
            # Initialize service
            if not self.engagement_board_detector.initialize():
                self.logger.error("Angajman tahtası dedektör servisi başlatılamadı")
                return
            
            self.logger.info("Angajman tahtası dedektör servisi başlatıldı - YOLO ve OCR aktif")
        else:
            # Reset detection_done flag if service exists
            self.engagement_board_detector.detection_done = False
            self.engagement_board_detector.ocr_text = ""
            self.engagement_board_detector.class_name = ""
            
        # Start service
        self.engagement_board_detector.start()
        
    def switch_to_engagement_mode(self, target_class):
        """
        EngagementBoardService'ten tespit tamamlandığında Engagement Mode'a geç.
        Sadece belirtilen sınıfı tespit et.
        """
        self.logger.info(f"Angajman tahtası tespiti tamamlandı, Angajman Mode'a geçiliyor. Hedef sınıf: {target_class}")
        
        # Engagement board detector'ü durdur
        if hasattr(self, 'engagement_board_detector') and self.engagement_board_detector:
            self.engagement_board_detector.stop()
            
        # Engagement mode detector'ü başlat ve hedef sınıfı ayarla
        self.init_engagement_detector(target_class)
        
        # Engagement mode butonunu seç, engagement board butonunu seçme
        self.menu_sidebar.engagement_dl_button.setChecked(True)
        self.menu_sidebar.engagement_board_button.setChecked(False)
        
        # Kamera görünümünü güncelle
        self.camera_view.set_detection_active(True)
        self.camera_view.set_detection_mode("engagement")

    def on_balloon_edge_clicked(self):
        """Handle balloon detection with edge/contour methods button click."""
        is_active = self.menu_sidebar.balloon_edge_button.isChecked()

        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.balloon_edge_button)
            self._stop_all_detection_services()

        if is_active:
            self.logger.info("Hareketli Balon Modu (Kenar/Kontur Yöntemi) aktif edildi")
            # BalloonClassicService başlat
            from services.balloon_classic_service import BalloonClassicService
            self.balloon_edge_service = BalloonClassicService()
            if hasattr(self, 'camera_service') and self.camera_service:
                self.camera_service.set_detector_service(self.balloon_edge_service)
            if not self.balloon_edge_service.initialize():
                self.logger.error("Klasik balon tespit servisi başlatılamadı!")
                return
            self.balloon_edge_service.start()
            self.camera_view.set_detection_active(True)
            self.camera_view.set_detection_mode("balloon_edge")
        else:
            self.logger.info("Hareketli Balon Modu (Kenar/Kontur Yöntemi) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)
            if hasattr(self, 'balloon_edge_service') and self.balloon_edge_service:
                self.balloon_edge_service.stop()

    def on_balloon_color_clicked(self):
        """Handle balloon detection with color segmentation button click."""
        is_active = self.menu_sidebar.balloon_color_button.isChecked()

        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.balloon_color_button)
            self._stop_all_detection_services()

        if is_active:
            self.logger.info("Hareketli Balon Modu (Renk Segmentasyon) aktif edildi")
            from services.balloon_color_service import BalloonColorService
            self.balloon_color_service = BalloonColorService()
            if hasattr(self, 'camera_service') and self.camera_service:
                self.camera_service.set_detector_service(self.balloon_color_service)
            if not self.balloon_color_service.initialize():
                self.logger.error("Renk segmentasyon balon tespit servisi başlatılamadı!")
                return
            self.balloon_color_service.start()
            self.camera_view.set_detection_active(True)
            self.camera_view.set_detection_mode("balloon_color")
        else:
            self.logger.info("Hareketli Balon Modu (Renk Segmentasyon) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)
            if hasattr(self, 'balloon_color_service') and self.balloon_color_service:
                self.balloon_color_service.stop()

    def on_servo_control_clicked(self):
        """Open the manual servo control dialog."""
        from ui.servo_control_dialog import ServoControlDialog
        
        # Log the action
        self.logger.info("Manuel servo kontrolü başlatılıyor")
        
        # Create and show the dialog
        dialog = ServoControlDialog(self)
        dialog.exec_()