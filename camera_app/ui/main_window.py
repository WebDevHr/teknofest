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
from services.yolo_service import YoloService
from services.shape_detection_service import ShapeDetectionService
from services.roboflow_service import RoboflowService
from ui.sidebar import LogSidebar, MenuSidebar, IconThemeManager
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
        
        # Set default theme
        self.current_theme = "dark"  # Default to dark theme
        
        # Create FPS display label - moved before apply_theme is called indirectly by init_ui
        self.init_fps_display()
        
        # Initialize UI components
        self.init_ui()
        
        # Initialize camera service
        self.init_camera()
        
        # Show the window in full screen mode instead of maximized
        self.showFullScreen()
        
        # Position the toggle buttons after showing the window
        self.update_toggle_button_positions()
        
        # Log that application has started
        self.logger.info("Application started in full screen mode")
        
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
        self.log_sidebar.clear_button.clicked.connect(self.on_clear_log)
        self.log_sidebar.setFixedWidth(0)  # Start with zero width
        
        # Connect logger signals to log sidebar
        self.logger.log_added.connect(self.log_sidebar.add_log)
        
        # Create right sidebar (Menu) - start with 0 width
        self.menu_sidebar = MenuSidebar(self)
        self.menu_sidebar.setFixedWidth(0)  # Start with zero width
        
        # Connect menu button signals
        self.menu_sidebar.settings_button.clicked.connect(self.on_settings_clicked)
        self.menu_sidebar.capture_button.clicked.connect(self.on_capture_clicked)
        self.menu_sidebar.save_button.clicked.connect(self.on_save_clicked)
        self.menu_sidebar.balloon_dl_button.clicked.connect(self.on_balloon_dl_clicked)
        self.menu_sidebar.balloon_classic_button.clicked.connect(self.on_balloon_classic_clicked)
        self.menu_sidebar.friend_foe_dl_button.clicked.connect(self.on_friend_foe_dl_clicked)
        self.menu_sidebar.friend_foe_classic_button.clicked.connect(self.on_friend_foe_classic_clicked)
        self.menu_sidebar.engagement_dl_button.clicked.connect(self.on_engagement_dl_clicked)
        self.menu_sidebar.engagement_hybrid_button.clicked.connect(self.on_engagement_hybrid_clicked)
        self.menu_sidebar.fps_button.clicked.connect(self.on_fps_clicked)
        self.menu_sidebar.theme_button.clicked.connect(self.toggle_theme)
        self.menu_sidebar.exit_button.clicked.connect(self.on_exit_clicked)
        self.menu_sidebar.emergency_stop_button.clicked.connect(self.on_emergency_stop_clicked)
        
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
        
        # Update FPS display style for dark theme
        self.fps_label.setStyleSheet("""
            color: white;
            background-color: rgba(0, 0, 0, 120);
            border-radius: 5px;
            padding: 2px 5px;
        """)
        
        # Set sidebar backgrounds
        self.log_sidebar.setStyleSheet("background-color: #333333;")
        self.menu_sidebar.setStyleSheet("background-color: #333333;")
        
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
        
        # Update FPS label style
        self.update_fps_label_style()
        
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
        
        # Update FPS display style for light theme
        self.fps_label.setStyleSheet("""
            color: black;
            background-color: rgba(255, 255, 255, 180);
            border-radius: 5px;
            padding: 2px 5px;
        """)
        
        # Set sidebar backgrounds
        self.log_sidebar.setStyleSheet("background-color: #E0E0E0;")
        self.menu_sidebar.setStyleSheet("background-color: #E0E0E0;")
        
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
        
        # Update FPS label style
        self.update_fps_label_style()
        
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
            
        # Use a lower FPS for better performance
        self.camera_service.start(fps=24)
    
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
        self.update_toggle_button_positions()
        
        # Update FPS label position when window is resized
        if hasattr(self, 'fps_label'):
            self.fps_label.move(20, self.height() - 50)
    
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
    
    def on_capture_clicked(self):
        """Handle Capture button click."""
        # Ekran görüntüsü alma işlevi (varsa)
        filename = None
        if hasattr(self, 'camera_service'):
            filename = self.camera_service.capture_image()
        
        # Sonuç iletişim kutusunu göster
        capture_dialog = QMessageBox(self)
        
        if filename:
            # Başarılı
            capture_dialog.setWindowTitle("Görüntü Yakalama Başarılı")
            capture_dialog.setIcon(QMessageBox.Information)
            capture_dialog.setText("Görüntü başarıyla yakalandı!")
            capture_dialog.setInformativeText(f"Şu isimle kaydedildi: {filename}")
            
            # Log
            self.logger.info(f"Görüntü yakalandı ve {filename} olarak kaydedildi")
        else:
            # Başarısız
            capture_dialog.setWindowTitle("Görüntü Yakalama Başarısız")
            capture_dialog.setIcon(QMessageBox.Warning)
            capture_dialog.setText("Görüntü yakalanırken hata oluştu.")
            capture_dialog.setInformativeText("Lütfen kameranın düzgün çalıştığını kontrol edin.")
            
            # Log
            self.logger.warning("Görüntü yakalama başarısız oldu")
        
        # Butonlar
        capture_dialog.setStandardButtons(QMessageBox.Ok)
        capture_dialog.button(QMessageBox.Ok).setText("Tamam")
        
        # İletişim kutusunu göster
        capture_dialog.exec_()
    
    def on_save_clicked(self):
        """Handle Save button click."""
        # Varsayılan dosya adını oluştur
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"kamera_goruntu_{timestamp}.jpg"
        
        # Kaydedilecek dosya adı/konumu seçme iletişim kutusu
        from PyQt5.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Mevcut Kareyi Kaydet",
            default_filename,
            "Görüntüler (*.png *.jpg *.jpeg)"
        )
        
        # Kullanıcı dosya seçtiyse kaydet
        if filename:
            success = False
            if hasattr(self, 'camera_service'):
                success = self.camera_service.save_current_frame(filename)
            
            # Sonuç iletişim kutusunu göster
            save_dialog = QMessageBox(self)
            
            if success:
                # Başarılı
                save_dialog.setWindowTitle("Kaydetme Başarılı")
                save_dialog.setIcon(QMessageBox.Information)
                save_dialog.setText("Mevcut kare başarıyla kaydedildi!")
                save_dialog.setInformativeText(f"Şu isimle kaydedildi: {filename}")
                
                # Log
                self.logger.info(f"Mevcut kare {filename} olarak kaydedildi")
            else:
                # Başarısız
                save_dialog.setWindowTitle("Kaydetme Başarısız")
                save_dialog.setIcon(QMessageBox.Warning)
                save_dialog.setText("Mevcut kare kaydedilemedi.")
                save_dialog.setInformativeText("Lütfen kameranın düzgün çalıştığını kontrol edin.")
                
                # Log
                self.logger.warning(f"Mevcut kare {filename} olarak kaydedilemedi")
            
            # Butonlar
            save_dialog.setStandardButtons(QMessageBox.Ok)
            save_dialog.button(QMessageBox.Ok).setText("Tamam")
            
            # İletişim kutusunu göster
            save_dialog.exec_()
        else:
            # Kullanıcı iptal etti
            self.logger.info("Kaydetme işlemi kullanıcı tarafından iptal edildi")
    
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
            self.logger.info("YOLO tespiti başlatıldı")
            button.setText("Tespiti Durdur")
        else:
            # YOLO tespitini durdur
            if hasattr(self, 'yolo_service'):
                self.yolo_service.stop()
                self.logger.info("YOLO tespiti durduruldu")
            button.setText("YOLO Tespiti")
    
    def init_yolo(self):
        """Initialize the YOLO service."""
        model_path = "C:\\Users\\Administrator\\Desktop\\gok-2025\\teknofest\\camera_app\\models\\bests_balloon_30_dark.pt"
        self.yolo_service = YoloService(model_path)
        
        # YOLO servisini kamera servisine bağla
        self.camera_service.set_yolo_service(self.yolo_service)
        
        # YOLO modelini başlat
        if not self.yolo_service.initialize():
            self.logger.error("YOLO modeli başlatılamadı")
            QMessageBox.warning(self, "YOLO Hatası", "YOLO modeli başlatılamadı. Model dosyasının var olduğunu kontrol edin.")
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
            self.logger.info("Şekil tespiti başlatıldı")
            button.setText("Tespiti Durdur")
        else:
            # Şekil tespitini durdur
            if hasattr(self, 'shape_detection_service'):
                self.shape_detection_service.stop()
                self.logger.info("Şekil tespiti durduruldu")
            button.setText("Şekil Tespiti")
    
    def init_roboflow(self):
        """Initialize the Roboflow service."""
        # Tam yolu belirtelim
        model_path = "C:\\Users\\Administrator\\Desktop\\gok-2025\\teknofest\\camera_app\\models\\engagement-best.pt"
        
        # Dosyanın varlığını kontrol edelim
        if not os.path.exists(model_path):
            self.logger.error(f"Roboflow modeli bulunamadı: {model_path}")
            QMessageBox.warning(self, "Roboflow Hatası", f"Roboflow modeli şu konumda bulunamadı: {model_path}\nLütfen model dosyasının var olduğundan emin olun.")
            return False
        
        self.roboflow_service = RoboflowService(model_path)
        
        # Roboflow servisini kamera servisine bağla
        self.camera_service.set_roboflow_service(self.roboflow_service)
        
        # Roboflow modelini başlat
        if not self.roboflow_service.initialize():
            self.logger.error("Roboflow modeli başlatılamadı")
            QMessageBox.warning(self, "Roboflow Hatası", "Roboflow modeli başlatılamadı. Model dosyasının geçerli olduğunu kontrol edin.")
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
            self.logger.info("Roboflow tespiti başlatıldı")
            button.setText("Tespiti Durdur")
        else:
            # Roboflow tespitini durdur
            if hasattr(self, 'roboflow_service'):
                self.roboflow_service.stop()
                self.logger.info("Roboflow tespiti durduruldu")
            button.setText("Roboflow Tespiti")
    
    def on_fps_clicked(self):
        """Handle FPS button click."""
        if hasattr(self, 'camera_service'):
            is_showing = self.camera_service.toggle_fps_display()
            button_text = "FPS Gizle" if is_showing else "FPS Göster"
            self.menu_sidebar.fps_button.setText(button_text)
            
            # Toggle visibility of our FPS label
            self.fps_label.setVisible(is_showing)
            
            self.logger.info(f"FPS gösterimi {'etkinleştirildi' if is_showing else 'devre dışı bırakıldı'}")
    
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
        
        # Log a confirmation message that will appear in the sidebar (but won't be visible until opened)
        self.logger.info("Log display initialized")
    
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
    
    def init_fps_display(self):
        """Initialize the FPS display label."""
        # Create the FPS label
        self.fps_label = QLabel("FPS: 0", self)
        self.fps_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        # Set initial position - will be properly repositioned in resizeEvent
        self.fps_label.move(20, 20)  # Start at a safe position
        
        # Style the label based on current theme if theme is already set
        if hasattr(self, 'current_theme'):
            self.update_fps_label_style()
        
        # Create timer to update the FPS
        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(500)  # Update twice per second
    
    def update_fps(self):
        """Update the FPS display."""
        if hasattr(self, 'camera_service'):
            fps = self.camera_service.fps
            self.fps_label.setText(f"FPS: {fps:.1f}")
    
    def update_fps_label_style(self):
        """Update the FPS label style based on current theme."""
        if self.current_theme == "dark":
            self.fps_label.setStyleSheet("""
                color: white;
                background-color: rgba(0, 0, 0, 120);
                border-radius: 5px;
                padding: 2px 5px;
            """)
        else:
            self.fps_label.setStyleSheet("""
                color: black;
                background-color: rgba(255, 255, 255, 180);
                border-radius: 5px;
                padding: 2px 5px;
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

    def on_balloon_dl_clicked(self):
        """Handle balloon detection with deep learning button click."""
        is_active = self.menu_sidebar.balloon_dl_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.balloon_dl_button)
        
        # This uses the existing YOLO service
        if is_active:
            self.logger.info("Hareketli Balon Modu (Derin Öğrenme) aktif edildi")
            self.init_yolo()  # Initialize YOLO if needed
            self.camera_view.set_detection_active(True)
            self.camera_view.set_detection_mode("yolo")
        else:
            self.logger.info("Hareketli Balon Modu (Derin Öğrenme) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)

    def on_balloon_classic_clicked(self):
        """Handle balloon detection with classical methods button click."""
        is_active = self.menu_sidebar.balloon_classic_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.balloon_classic_button)
            
        if is_active:
            self.logger.info("Hareketli Balon Modu (Klasik Yöntemler) aktif edildi")
            self.camera_view.set_detection_active(False)  # Currently just shows camera feed
        else:
            self.logger.info("Hareketli Balon Modu (Klasik Yöntemler) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)

    def on_friend_foe_dl_clicked(self):
        """Handle friend/foe detection with deep learning button click."""
        is_active = self.menu_sidebar.friend_foe_dl_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.friend_foe_dl_button)
            
        if is_active:
            self.logger.info("Hareketli Dost/Düşman Modu (Derin Öğrenme) aktif edildi")
            self.camera_view.set_detection_active(False)  # Currently just shows camera feed
        else:
            self.logger.info("Hareketli Dost/Düşman Modu (Derin Öğrenme) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)

    def on_friend_foe_classic_clicked(self):
        """Handle friend/foe detection with classical methods button click."""
        is_active = self.menu_sidebar.friend_foe_classic_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.friend_foe_classic_button)
            
        if is_active:
            self.logger.info("Hareketli Dost/Düşman Modu (Klasik Yöntemler) aktif edildi")
            self.camera_view.set_detection_active(False)  # Currently just shows camera feed
        else:
            self.logger.info("Hareketli Dost/Düşman Modu (Klasik Yöntemler) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)

    def on_engagement_dl_clicked(self):
        """Handle engagement detection with deep learning button click."""
        is_active = self.menu_sidebar.engagement_dl_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.engagement_dl_button)
        
        # This uses the existing Roboflow service
        if is_active:
            self.logger.info("Angajman Modu (Derin Öğrenme) aktif edildi")
            self.init_roboflow()  # Initialize Roboflow if needed
            self.camera_view.set_detection_active(True)
            self.camera_view.set_detection_mode("roboflow")
        else:
            self.logger.info("Angajman Modu (Derin Öğrenme) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)

    def on_engagement_hybrid_clicked(self):
        """Handle engagement detection with hybrid methods button click."""
        is_active = self.menu_sidebar.engagement_hybrid_button.isChecked()
        
        # Uncheck other buttons
        if is_active:
            self._uncheck_other_detection_buttons(self.menu_sidebar.engagement_hybrid_button)
            
        if is_active:
            self.logger.info("Angajman Modu (Hibrit) aktif edildi")
            self.camera_view.set_detection_active(False)  # Currently just shows camera feed
        else:
            self.logger.info("Angajman Modu (Hibrit) devre dışı bırakıldı")
            self.camera_view.set_detection_active(False)
    
    def _uncheck_other_detection_buttons(self, current_button):
        """Uncheck all detection buttons except the current one."""
        buttons = [
            self.menu_sidebar.balloon_dl_button,
            self.menu_sidebar.balloon_classic_button,
            self.menu_sidebar.friend_foe_dl_button,
            self.menu_sidebar.friend_foe_classic_button,
            self.menu_sidebar.engagement_dl_button,
            self.menu_sidebar.engagement_hybrid_button
        ]
        
        for button in buttons:
            if button != current_button:
                button.setChecked(False) 