#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sidebar Component
----------------
Reusable sidebar component for the camera application.
"""

import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, QHBoxLayout, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer, QSize, QPointF, QRect, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPainterPath, QPen, QBrush, QFont

class IconThemeManager:
    """Class for handling theme-aware icons."""
    
    @staticmethod
    def get_themed_icon(icon_path, is_dark_theme=True):
        """Get a themed icon with appropriate color based on current theme."""
        if not os.path.exists(icon_path):
            return QIcon()
            
        # Load the original icon
        pixmap = QPixmap(icon_path)
        
        # Create a transparent version
        result = QPixmap(pixmap.size())
        result.fill(Qt.transparent)
        
        # Create painter for the result
        painter = QPainter(result)
        
        # Set the color based on theme
        if is_dark_theme:
            # For dark theme, use white icons
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(result.rect(), QColor(255, 255, 255, 255))  # White
        else:
            # For light theme, use dark icons
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(result.rect(), QColor(33, 33, 33, 255))  # Dark gray/black
        
        # End painting
        painter.end()
        
        return QIcon(result)

class Sidebar(QWidget):
    """
    Reusable sidebar component.
    Implements the Strategy pattern for different sidebar behaviors.
    """
    # Signals
    animation_value_changed = pyqtSignal(int)
    
    def __init__(self, parent=None, position="left", width=250):
        super().__init__(parent)
        self.position = position
        self.target_width = width
        self.is_open = False
        
        # Set initial width to 0 (closed)
        self.setFixedWidth(0)
        
        # Set background color
        self.setStyleSheet("background-color: #333333;")
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Initialize animation
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.valueChanged.connect(self._on_animation_value_changed)
    
    def _on_animation_value_changed(self, value):
        """Handle animation value changes."""
        self.animation_value_changed.emit(value)
    
    def toggle(self):
        """Toggle the sidebar open/closed state."""
        target_width = self.target_width if not self.is_open else 0
        
        # Configure animation
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(target_width)
        
        # Start animation
        self.animation.start()
        
        # Update state
        self.is_open = not self.is_open
        
        return self.is_open
    
    def add_widget(self, widget):
        """Add a widget to the sidebar."""
        self.layout.addWidget(widget)
    
    def add_stretch(self):
        """Add a stretch to the sidebar layout."""
        self.layout.addStretch()


class LogSidebar(Sidebar):
    """Log sidebar implementation."""
    
    def __init__(self, parent=None):
        super().__init__(parent, position="left", width=400)  # Increased width for better readability
        
        # Base directory for icons - use absolute path
        self.icon_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
        
        # Track the number of displayed logs to avoid unnecessary refreshes
        self.displayed_log_count = 0
        
        # Add header label
        self.header_label = QLabel("Uygulama Logları")
        self.header_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
            padding: 5px;
            margin-bottom: 10px;
            background-color: transparent;
        """)
        self.add_widget(self.header_label)
        
        # Create log text area with enhanced styling
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.update_text_area_style(is_dark=True)  # Default to dark theme
        self.add_widget(self.log_text)
        
        # Set custom document handling to colorize log levels
        self.log_text.document().setDefaultStyleSheet("""
            .info { color: #2ecc71; }  /* Green */
            .warning { color: #f39c12; }  /* Orange/Yellow */
            .error { color: #e74c3c; }  /* Red */
            .timestamp { color: #3498db; font-weight: bold; }  /* Blue */
        """)
        
        # Setup timer to ensure logs are updated regularly
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_logs)
        self.refresh_timer.start(500)  # Refresh every 500ms
    
    def update_text_area_style(self, is_dark=True):
        """Update the text area style based on theme."""
        if is_dark:
            self.log_text.setStyleSheet("""
                QTextEdit {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                    border: 1px solid #34495e;
                    border-radius: 5px;
                    padding: 8px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 12px;
                    line-height: 1.4;
                }
                
                QTextEdit QScrollBar:vertical {
                    border: none;
                    background: #34495e;
                    width: 10px;
                    margin: 0px;
                }
                
                QTextEdit QScrollBar::handle:vertical {
                    background: #7f8c8d;
                    min-height: 30px;
                    border-radius: 5px;
                }
                
                QTextEdit QScrollBar::handle:vertical:hover {
                    background: #95a5a6;
                }
                
                QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                
                QTextEdit QScrollBar::add-page:vertical, QTextEdit QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)
            self.header_label.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: white;
                padding: 5px;
                margin-bottom: 10px;
                background-color: transparent;
            """)
        else:
            self.log_text.setStyleSheet("""
                QTextEdit {
                    background-color: #f8f9fa;
                    color: #343a40;
                    border: 1px solid #ced4da;
                    border-radius: 5px;
                    padding: 8px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 12px;
                    line-height: 1.4;
                }
                
                QTextEdit QScrollBar:vertical {
                    border: none;
                    background: #e9ecef;
                    width: 10px;
                    margin: 0px;
                }
                
                QTextEdit QScrollBar::handle:vertical {
                    background: #adb5bd;
                    min-height: 30px;
                    border-radius: 5px;
                }
                
                QTextEdit QScrollBar::handle:vertical:hover {
                    background: #868e96;
                }
                
                QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                
                QTextEdit QScrollBar::add-page:vertical, QTextEdit QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)
            self.header_label.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: #343a40;
                padding: 5px;
                margin-bottom: 10px;
                background-color: transparent;
            """)
    
    def add_log(self, message):
        """Add a log message to the text area with colorized formatting."""
        # Format the message with HTML for colorization
        formatted_html = self.format_log_message(message)
        
        # Add the formatted message
        self.log_text.append(formatted_html)
        
        # Increment the displayed log count
        self.displayed_log_count += 1
        
        # Auto-scroll to the bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def format_log_message(self, message):
        """Format a log message with HTML styling based on log level."""
        try:
            # Extract parts of the log message
            timestamp_end = message.find(']') + 1
            if timestamp_end > 0 and '[' in message:
                timestamp = message[:timestamp_end]
                content = message[timestamp_end:].strip()
                
                # Determine log level
                level_class = 'info'
                if '[WARNING]' in timestamp:
                    level_class = 'warning'
                elif '[ERROR]' in timestamp:
                    level_class = 'error'
                
                # Format with HTML
                return f'<span class="timestamp">{timestamp}</span> <span class="{level_class}">{content}</span>'
            else:
                # Fallback for unformatted messages
                return message
        except Exception:
            # Fallback in case of parsing error
            return message
    
    def clear_logs(self):
        """Clear the log text area."""
        self.log_text.clear()
        self.displayed_log_count = 0
    
    def refresh_logs(self):
        """Ensure logs are displayed and updated by fetching the latest logs from LoggerService."""
        # Import here to avoid circular import
        from services.logger_service import LoggerService
        
        # Get the logger service instance and fetch all logs
        logger = LoggerService()
        all_logs = logger.get_logs()
        
        # Check if there are new logs to display
        if len(all_logs) > self.displayed_log_count:
            # Save the current scroll position
            scrollbar = self.log_text.verticalScrollBar()
            was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 10  # Consider "at bottom" if within 10 pixels
            scroll_position = scrollbar.value()
            
            # Clear and refill the log view
            self.log_text.clear()
            for log in all_logs:
                formatted_html = self.format_log_message(log)
                self.log_text.append(formatted_html)
            
            # Update the displayed log count
            self.displayed_log_count = len(all_logs)
            
            # Restore scroll position or keep at bottom if it was at bottom
            if was_at_bottom:
                scrollbar.setValue(scrollbar.maximum())
            else:
                scrollbar.setValue(scroll_position)
        
        # Force update of the text edit
        self.log_text.update()


class MenuSidebar(Sidebar):
    """Menu sidebar implementation."""
    
    def __init__(self, parent=None):
        super().__init__(parent, position="right", width=280)
        
        # Flag to track current theme
        self.is_dark_theme = True
        
        # Base directory for icons - use absolute path
        self.icon_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
        
        # Buton stilini ayarlamak için QSS stil sayfası
        self.button_style = """
            QPushButton {
                padding-left: 10px;
            }
        """
        
        # Create menu buttons with icons
        moon_icon_path = os.path.join(self.icon_base_dir, "moon.png")
        self.theme_button = self.create_icon_button("", moon_icon_path, icon_only=True)
        self.settings_button = self.create_icon_button("", os.path.join(self.icon_base_dir, "settings.png"), icon_only=True)
        self.exit_button = self.create_icon_button("", os.path.join(self.icon_base_dir, "exit.png"), icon_only=True)
        
        # Create a horizontal layout for the top buttons
        self.top_buttons_layout = QHBoxLayout()
        self.top_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.top_buttons_layout.setSpacing(5)
        self.top_buttons_layout.addWidget(self.theme_button)
        self.top_buttons_layout.addWidget(self.settings_button)
        self.top_buttons_layout.addWidget(self.exit_button)
        
        # Create a widget to hold the horizontal layout
        self.top_buttons_widget = QWidget()
        self.top_buttons_widget.setLayout(self.top_buttons_layout)
        self.top_buttons_widget.setStyleSheet("""
            background-color: transparent;
            border-radius: 8px;
            padding: 5px;
            margin-bottom: 10px;
        """)
        
        # Create dividers and section titles
        self.create_divider = lambda: self.create_divider_widget()
        
        # Aşama başlıkları oluştur
        self.create_stage_title = lambda text: self.create_title_widget(text)
        
        # İkon yolları - artık dinamik olarak oluşturacağız
        # İkonları oluştur
        balloon_icon = self.create_balloon_icon()  # 1. Aşama için yeşil balon
        friend_foe_icon = self.create_dual_balloon_icon()  # 2. Aşama için mavi-kırmızı balonlar
        shapes_icon = self.create_shapes_icon()  # 3. Aşama için kırmızı kare, yeşil daire, mavi üçgen
        
        # Create detection mode buttons with two-line text
        self.balloon_dl_button = self.create_icon_button("Hareketli Balon Mode\n(Derin Öğrenmeli)", 
                                              balloon_icon, checkable=True)
        self.balloon_edge_button = self.create_icon_button("Hareketli Balon Mode\n(Kenar/Kontur Yöntemi)", 
                                              balloon_icon, checkable=True)
        self.balloon_color_button = self.create_icon_button("Hareketli Balon Mode\n(Renk Segmentasyon)", 
                                              balloon_icon, checkable=True)
        self.balloon_classic_button = self.create_icon_button("Hareketli Balon Mode\n(Klasik Yöntemler)", 
                                              balloon_icon, checkable=True)
        self.friend_foe_dl_button = self.create_icon_button("Hareketli Dost/Düşman Mode\n(Derin Öğrenmeli)", 
                                              friend_foe_icon, checkable=True)
        self.friend_foe_classic_button = self.create_icon_button("Hareketli Dost/Düşman Mode\n(Klasik Yöntemler)", 
                                              friend_foe_icon, checkable=True)
        self.engagement_dl_button = self.create_icon_button("Angajman Mode\n(Derin Öğrenmeli)", 
                                              shapes_icon, checkable=True)
        self.engagement_hybrid_button = self.create_icon_button("Angajman Mode\n(Hibrit)", 
                                              shapes_icon, checkable=True)
        self.engagement_board_button = self.create_icon_button("Angajman Tahtası Okuması", 
                                              shapes_icon, checkable=True)
        
        # Create bottom action buttons with icons only
        self.save_button = self.create_icon_button("", os.path.join(self.icon_base_dir, "save.png"), icon_only=True)
        self.save_button.setToolTip("Kaydet")
        
        # Servo kontrol butonu - 4'lü ok ikonu ile
        controls_icon = self.create_controls_icon()
        self.servo_control_button = self.create_icon_button("", controls_icon, icon_only=True)
        self.servo_control_button.setToolTip("Manuel Servo Kontrolü")
        
        # FPS göstergesi - butonlara benzer bir stil ile
        self.fps_label = QLabel("0", self)
        self.fps_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.fps_label.setAlignment(Qt.AlignCenter)
        self.fps_label.setFixedSize(36, 36)  # Butonlarla aynı boyut
        self.fps_label.setToolTip("Frames Per Second")
        
        # Label'a hafif bir gölge ekle - 3D görünüm için
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(5)
        shadow.setColor(QColor(0, 0, 0, 50))  # Yarı saydam siyah
        shadow.setOffset(1, 1)
        self.fps_label.setGraphicsEffect(shadow)
        
        # Tracking button özel ikon ile oluştur (target.png mevcut değil)
        tracking_icon = self.create_tracking_icon()
        self.tracking_button = self.create_icon_button("Takibi Başlat", tracking_icon, checkable=True)
        self.tracking_button.setToolTip("Hedef Takibi Modu")
        
        # PBVS Tracking butonu - tam genişlikte diğer toggle butonlar gibi
        pbvs_icon = self.create_pbvs_icon()
        self.pbvs_tracking_button = self.create_icon_button("PBVS Takip", pbvs_icon, checkable=True)
        self.pbvs_tracking_button.setToolTip("Position-Based Visual Servoing Takip Modu")
        
        # Create a horizontal layout for the bottom buttons
        self.bottom_buttons_layout = QHBoxLayout()
        self.bottom_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_buttons_layout.setSpacing(5)
        self.bottom_buttons_layout.addWidget(self.fps_label)  # FPS göstergesi sola alındı
        self.bottom_buttons_layout.addWidget(self.servo_control_button)
        self.bottom_buttons_layout.addWidget(self.save_button)  # Save butonu sona alındı
        
        # Tüm butonların eşit boyutlara sahip olduğundan emin ol
        for button in [self.servo_control_button, self.save_button]:
            button.setFixedSize(36, 36)
            button.setIconSize(QSize(24, 24))
        
        # Create a widget to hold the bottom layout
        self.bottom_buttons_widget = QWidget()
        self.bottom_buttons_widget.setLayout(self.bottom_buttons_layout)
        self.bottom_buttons_widget.setStyleSheet("""
            background-color: transparent;
            border-radius: 8px;
            padding: 5px;
            margin-top: 10px;
        """)
        
        # Store buttons for theme updates
        self.buttons = [
            self.theme_button, self.settings_button, self.exit_button,
            self.save_button, self.servo_control_button,
            self.balloon_dl_button, self.balloon_edge_button, self.balloon_color_button, self.balloon_classic_button,
            self.friend_foe_dl_button, self.friend_foe_classic_button,
            self.engagement_dl_button, self.engagement_hybrid_button,
            self.engagement_board_button, self.tracking_button, self.pbvs_tracking_button
        ]
        
        # Store icons paths and alternates for theme updates
        self.button_icons = {
            self.theme_button: {"dark": os.path.join(self.icon_base_dir, "moon.png"), 
                                "light": os.path.join(self.icon_base_dir, "sun.png")},
            self.settings_button: os.path.join(self.icon_base_dir, "settings.png"),
            self.exit_button: os.path.join(self.icon_base_dir, "exit.png"),
            self.save_button: os.path.join(self.icon_base_dir, "save.png"),
            self.servo_control_button: controls_icon,
            self.tracking_button: tracking_icon,  # Özel oluşturulan ikonu kullan
            self.pbvs_tracking_button: pbvs_icon,
            self.balloon_dl_button: balloon_icon,
            self.balloon_edge_button: balloon_icon,
            self.balloon_color_button: balloon_icon,
            self.balloon_classic_button: balloon_icon,
            self.friend_foe_dl_button: friend_foe_icon,
            self.friend_foe_classic_button: friend_foe_icon,
            self.engagement_dl_button: shapes_icon,
            self.engagement_hybrid_button: shapes_icon,
            self.engagement_board_button: shapes_icon
        }
        
        # Add buttons to sidebar in the requested order
        self.add_widget(self.top_buttons_widget)
        self.add_widget(self.create_divider())
        
        # Add stretch to center the detection mode buttons vertically
        self.add_stretch()
        
        # Add detection mode buttons in the middle - with dividers and titles
        # İlk grup - Balon
        self.add_widget(self.create_stage_title("1. Aşama"))
        self.add_widget(self.balloon_dl_button)
        self.add_widget(self.balloon_edge_button)
        self.add_widget(self.balloon_color_button)
        self.add_widget(self.balloon_classic_button)
        
        # Divider ekle
        self.add_widget(self.create_divider())
        
        # İkinci grup - Dost/Düşman
        self.add_widget(self.create_stage_title("2. Aşama"))
        self.add_widget(self.friend_foe_dl_button)
        self.add_widget(self.friend_foe_classic_button)
        
        # Divider ekle
        self.add_widget(self.create_divider())
        
        # Üçüncü grup - Angajman
        self.add_widget(self.create_stage_title("3. Aşama"))
        self.add_widget(self.engagement_dl_button)
        self.add_widget(self.engagement_hybrid_button)
        self.add_widget(self.engagement_board_button)
        
        # Divider ekle
        self.add_widget(self.create_divider())
        
        # Sistem Kontrolleri
        self.add_widget(self.create_stage_title("Sistem Kontrolleri"))
        
        # Tracking butonu - tam genişlikte diğer toggle butonlar gibi
        tracking_icon = self.create_tracking_icon()
        self.tracking_button = self.create_icon_button("Balon Takibi", tracking_icon, checkable=True)
        self.tracking_button.setToolTip("Balon Takibi Modu")
        self.add_widget(self.tracking_button)
        
        # PBVS Tracking butonu - tam genişlikte diğer toggle butonlar gibi
        pbvs_icon = self.create_pbvs_icon()
        self.pbvs_tracking_button = self.create_icon_button("PBVS Takip", pbvs_icon, checkable=True)
        self.pbvs_tracking_button.setToolTip("Position-Based Visual Servoing Takip Modu")
        self.add_widget(self.pbvs_tracking_button)
        
        # Create emergency stop button with warning icon
        self.emergency_stop_button = QPushButton("   ACİL STOP")  # Boşluklu metin ekle
        self.emergency_stop_button.setStyleSheet("""
            QPushButton {
                background-color: #FF0000;
                color: white;
                font-weight: bold;
                font-size: 14px;
                text-align: center;
                border-radius: 5px;
                padding: 8px 8px 8px 8px;  
                margin: 10px 5px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
            QPushButton:pressed {
                background-color: #AA0000;
            }
        """)
        
        # Acil stop ikonu oluştur
        self.create_warning_icon_for_button(self.emergency_stop_button)
        
        self.add_widget(self.emergency_stop_button)
        
        # Add stretch to keep the buttons centered
        self.add_stretch()
        
        # Add emergency stop and bottom buttons at the bottom
        self.add_widget(self.bottom_buttons_widget)

    def create_divider_widget(self):
        """Create a divider widget."""
        divider = QWidget()
        divider.setFixedHeight(2)  # Biraz daha kalın
        divider.setStyleSheet("""
            background-color: #666666; 
            margin: 12px 15px;
            border-radius: 1px;
        """)
        return divider
    
    def create_title_widget(self, text):
        """Create a title widget for sections."""
        title = QLabel(text)
        title.setStyleSheet("""
            color: #FF9800;
            font-weight: bold;
            font-size: 16px;
            margin: 10px 5px 5px 5px;
            padding-left: 5px;
            background-color: transparent;
        """)
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return title
    
    def create_balloon_icon(self):
        """1. Aşama için yeşil balon ikonu oluştur."""
        icon_size = QSize(32, 32)
        pixmap = QPixmap(icon_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Yeşil balon çiz
        balloon_color = QColor(40, 180, 70)  # Yeşil
        painter.setPen(QPen(QColor(30, 150, 50), 1.5))  # Koyu yeşil kenar
        painter.setBrush(QBrush(balloon_color))
        
        # Daire şeklinde balon
        balloon_rect = QRect(4, 4, 24, 24)
        painter.drawEllipse(balloon_rect)
        
        # Balonun ipini çiz
        painter.setPen(QPen(QColor(30, 150, 50), 1.5))
        painter.drawLine(QPoint(16, 28), QPoint(16, 32))
        
        painter.end()
        return QIcon(pixmap)
    
    def create_dual_balloon_icon(self):
        """2. Aşama için mavi ve kırmızı balon ikonu oluştur."""
        icon_size = QSize(32, 32)
        pixmap = QPixmap(icon_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Mavi balon
        blue_balloon_color = QColor(30, 120, 220)  # Mavi
        painter.setPen(QPen(QColor(20, 90, 180), 1.5))  # Koyu mavi kenar
        painter.setBrush(QBrush(blue_balloon_color))
        blue_balloon_rect = QRect(2, 4, 18, 18)
        painter.drawEllipse(blue_balloon_rect)
        
        # Mavi balonun ipi
        painter.setPen(QPen(QColor(20, 90, 180), 1.5))
        painter.drawLine(QPoint(11, 22), QPoint(11, 26))
        
        # Kırmızı balon
        red_balloon_color = QColor(220, 50, 50)  # Kırmızı
        painter.setPen(QPen(QColor(180, 30, 30), 1.5))  # Koyu kırmızı kenar
        painter.setBrush(QBrush(red_balloon_color))
        red_balloon_rect = QRect(12, 8, 18, 18)
        painter.drawEllipse(red_balloon_rect)
        
        # Kırmızı balonun ipi
        painter.setPen(QPen(QColor(180, 30, 30), 1.5))
        painter.drawLine(QPoint(21, 26), QPoint(21, 30))
        
        painter.end()
        return QIcon(pixmap)
    
    def create_shapes_icon(self):
        """3. Aşama için kırmızı kare, yeşil daire ve mavi üçgen ikonu oluştur."""
        icon_size = QSize(32, 32)
        pixmap = QPixmap(icon_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Kırmızı kare
        red_color = QColor(220, 50, 50)  # Kırmızı
        painter.setPen(QPen(QColor(180, 30, 30), 1.5))  # Koyu kırmızı kenar
        painter.setBrush(QBrush(red_color))
        square_rect = QRect(2, 6, 12, 12)
        painter.drawRect(square_rect)
        
        # Yeşil daire
        green_color = QColor(40, 180, 70)  # Yeşil
        painter.setPen(QPen(QColor(30, 150, 50), 1.5))  # Koyu yeşil kenar
        painter.setBrush(QBrush(green_color))
        circle_rect = QRect(18, 6, 12, 12)
        painter.drawEllipse(circle_rect)
        
        # Mavi üçgen
        blue_color = QColor(30, 120, 220)  # Mavi
        painter.setPen(QPen(QColor(20, 90, 180), 1.5))  # Koyu mavi kenar
        painter.setBrush(QBrush(blue_color))
        
        # Üçgen için noktalar
        triangle = QPainterPath()
        triangle.moveTo(16, 22)  # Üst nokta
        triangle.lineTo(8, 32)   # Sol alt
        triangle.lineTo(24, 32)  # Sağ alt
        triangle.lineTo(16, 22)  # Tekrar üst nokta
        painter.drawPath(triangle)
        
        painter.end()
        return QIcon(pixmap)
    
    def create_controls_icon(self):
        """4'lü ok ikonu oluştur (servo kontrolü için)."""
        icon_size = QSize(32, 32)
        pixmap = QPixmap(icon_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Beyaz arka plan olan biraz daha büyük bir daire çiz
        if self.is_dark_theme:
            painter.setPen(QPen(QColor(80, 80, 80), 1))
            painter.setBrush(QBrush(QColor(70, 70, 70)))
        else:
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.setBrush(QBrush(QColor(230, 230, 230)))
            
        painter.drawEllipse(QRect(1, 1, 30, 30))
        
        # Oklar için kalem ayarla
        if self.is_dark_theme:
            painter.setPen(QPen(QColor(220, 220, 220), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        else:
            painter.setPen(QPen(QColor(60, 60, 60), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        
        # Yukarı ok
        painter.drawLine(16, 5, 16, 13)
        painter.drawLine(16, 5, 12, 9)
        painter.drawLine(16, 5, 20, 9)
        
        # Sağ ok
        painter.drawLine(19, 16, 27, 16)
        painter.drawLine(27, 16, 23, 12)
        painter.drawLine(27, 16, 23, 20)
        
        # Aşağı ok
        painter.drawLine(16, 19, 16, 27)
        painter.drawLine(16, 27, 12, 23)
        painter.drawLine(16, 27, 20, 23)
        
        # Sol ok
        painter.drawLine(5, 16, 13, 16)
        painter.drawLine(5, 16, 9, 12)
        painter.drawLine(5, 16, 9, 20)
        
        painter.end()
        return QIcon(pixmap)
    
    def create_tracking_icon(self):
        """Balon takibi için hedef/crosshair ikonu oluştur."""
        icon_size = QSize(24, 24)
        pixmap = QPixmap(icon_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # İkon merkezleme için referans noktası
        center_x = 12
        center_y = 12
        
        # Hedef için kalem ayarla
        if self.is_dark_theme:
            crosshair_color = QColor(220, 220, 220)  # Beyaz tona yakın
        else:
            crosshair_color = QColor(60, 60, 60)     # Siyah tona yakın
        
        # İç daire çiz (hedef) - merkeze göre konumlandırılmış
        outer_radius = 7
        crosshair_outer = QRect(center_x - outer_radius, center_y - outer_radius, 
                               outer_radius * 2, outer_radius * 2)
        painter.setPen(QPen(crosshair_color, 1.5))
        painter.setBrush(Qt.transparent)
        painter.drawEllipse(crosshair_outer)
        
        # İç merkez daire - merkeze göre konumlandırılmış
        inner_radius = 2
        crosshair_inner = QRect(center_x - inner_radius, center_y - inner_radius, 
                                inner_radius * 2, inner_radius * 2)
        painter.setBrush(crosshair_color)
        painter.drawEllipse(crosshair_inner)
        
        # Artı işareti (nişan çizgileri)
        painter.setPen(QPen(crosshair_color, 1.2))
        
        # Yatay çizgiler - merkeze göre konumlandırılmış
        line_inner_gap = outer_radius + 1  # Dairenin biraz dışından başlat
        line_outer_len = 4                 # Dış çizgi uzunluğu
        
        # Sol yatay çizgi
        painter.drawLine(center_x - line_inner_gap - line_outer_len, center_y, 
                         center_x - line_inner_gap, center_y)
        
        # Sağ yatay çizgi
        painter.drawLine(center_x + line_inner_gap, center_y, 
                         center_x + line_inner_gap + line_outer_len, center_y)
        
        # Üst dikey çizgi
        painter.drawLine(center_x, center_y - line_inner_gap - line_outer_len, 
                         center_x, center_y - line_inner_gap)
        
        # Alt dikey çizgi
        painter.drawLine(center_x, center_y + line_inner_gap, 
                         center_x, center_y + line_inner_gap + line_outer_len)
        
        painter.end()
        return QIcon(pixmap)
    
    def create_pbvs_icon(self):
        """PBVS (Position-Based Visual Servoing) takibi için 3D koordinat sistemi ikonu oluştur."""
        icon_size = QSize(24, 24)
        pixmap = QPixmap(icon_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # İkon merkezleme için referans noktası
        center_x = 12
        center_y = 12
        
        # Renk ayarları
        if self.is_dark_theme:
            axes_color = QColor(220, 220, 220)  # Beyaz tona yakın
            x_color = QColor(255, 100, 100)     # Kırmızı
            y_color = QColor(100, 255, 100)     # Yeşil
            z_color = QColor(100, 100, 255)     # Mavi
        else:
            axes_color = QColor(60, 60, 60)     # Siyah tona yakın
            x_color = QColor(200, 50, 50)       # Kırmızı
            y_color = QColor(50, 200, 50)       # Yeşil
            z_color = QColor(50, 50, 200)       # Mavi
        
        # 3B koordinat sistemi çiz (izometrik perspektifli)
        # X ekseni (sağa)
        painter.setPen(QPen(x_color, 1.8))
        painter.drawLine(center_x, center_y, center_x + 10, center_y)
        
        # X ekseni ok başı
        points_x = [
            QPoint(center_x + 10, center_y), 
            QPoint(center_x + 7, center_y - 2),
            QPoint(center_x + 7, center_y + 2),
        ]
        painter.setBrush(x_color)
        painter.drawPolygon(points_x)
        
        # Y ekseni (yukarı)
        painter.setPen(QPen(y_color, 1.8))
        painter.drawLine(center_x, center_y, center_x, center_y - 10)
        
        # Y ekseni ok başı
        points_y = [
            QPoint(center_x, center_y - 10), 
            QPoint(center_x - 2, center_y - 7),
            QPoint(center_x + 2, center_y - 7),
        ]
        painter.setBrush(y_color)
        painter.drawPolygon(points_y)
        
        # Z ekseni (derinlik - sol alt)
        painter.setPen(QPen(z_color, 1.8))
        painter.drawLine(center_x, center_y, center_x - 7, center_y + 7)
        
        # Z ekseni ok başı
        points_z = [
            QPoint(center_x - 7, center_y + 7),
            QPoint(center_x - 4, center_y + 5),
            QPoint(center_x - 7, center_y + 4),
        ]
        painter.setBrush(z_color)
        painter.drawPolygon(points_z)
        
        # Merkez nokta
        painter.setPen(Qt.NoPen)
        painter.setBrush(axes_color)
        painter.drawEllipse(QRect(center_x - 2, center_y - 2, 4, 4))
        
        painter.end()
        return QIcon(pixmap)
    
    def create_icon_button(self, text, icon_path_or_icon, checkable=False, icon_only=False):
        """Create a button with a theme-aware icon."""
        button = QPushButton(text)
        
        # Icon can now be a QIcon object or a path
        if isinstance(icon_path_or_icon, QIcon):
            # Hazır ikon nesnesi kullan
            button.setIcon(icon_path_or_icon)
            button.setIconSize(QSize(28, 28))
        elif os.path.exists(icon_path_or_icon):
            # Dosyadan ikon yükle
            # Create a themed icon based on current theme
            icon = IconThemeManager.get_themed_icon(icon_path_or_icon, self.is_dark_theme)
            button.setIcon(icon)
            button.setIconSize(QSize(28, 28))
        else:
            # Use first letter of each word as a fallback
            fallback = ''.join([word[0] for word in text.split() if word])
            button.setText(f"[{fallback}] {text}")
        
        # İkon ve metin arasındaki boşluğu artır
        if not icon_only and text:
            # İki satır varsa her iki satırın da başında boşluk olmasını sağla
            if "\n" in text:
                # Metni satırlara ayır
                lines = text.split("\n")
                # Her satırın başına boşluk ekleyip birleştir
                formatted_text = "   " + lines[0] + "\n   " + lines[1]
                button.setText(formatted_text)
            else:
                # Normal CSS padding kullanımı yerine ikondan sonra boşluk ekleyen bir yaklaşım
                button.setText("   " + text)
        
        # Set checkable if needed
        if checkable:
            button.setCheckable(True)
            
            # Create a complete stylesheet for checkable buttons with theme-aware colors
            if self.is_dark_theme:
                button.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 12px;
                        padding-right: 8px;
                        padding-top: 4px;
                        padding-bottom: 4px;
                        color: white;
                        font-size: 13px;
                        font-weight: normal;
                        min-height: 32px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #444444;
                    }
                    QPushButton:checked {
                        background-color: #4CAF50;
                        color: white;
                        font-weight: bold;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 12px;
                        padding-right: 8px;
                        padding-top: 4px;
                        padding-bottom: 4px;
                        color: #333333;
                        font-size: 13px;
                        font-weight: normal;
                        min-height: 32px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #e0e0e0;
                    }
                    QPushButton:checked {
                        background-color: #4CAF50;
                        color: white;
                        font-weight: bold;
                    }
                """)
        elif icon_only:
            # Style for icon-only buttons - alt ve üst butonlar için yuvarlak stil
            if self.is_dark_theme:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #444444;
                        border-radius: 18px;
                        padding: 5px;
                        min-width: 36px;
                        min-height: 36px;
                        max-width: 36px;
                        max-height: 36px;
                    }
                    QPushButton:hover {
                        background-color: #555555;
                    }
                    QPushButton:pressed {
                        background-color: #666666;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border-radius: 18px;
                        padding: 5px;
                        min-width: 36px;
                        min-height: 36px;
                        max-width: 36px;
                        max-height: 36px;
                    }
                    QPushButton:hover {
                        background-color: #d0d0d0;
                    }
                    QPushButton:pressed {
                        background-color: #c0c0c0;
                    }
                """)
        else:
            # Simple stylesheet for non-checkable buttons with theme-aware colors
            if self.is_dark_theme:
                button.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 16px;
                        color: white;
                    }
                    QPushButton:hover {
                        background-color: #444444;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 16px;
                        color: #333333;
                    }
                    QPushButton:hover {
                        background-color: #e0e0e0;
                    }
                """)
        
        return button
    
    def create_warning_icon_for_button(self, button):
        """Acil stop butonu için uyarı üçgeni ikonu oluştur."""
        # İkon oluştur
        icon_size = QSize(24, 24)
        pixmap = QPixmap(icon_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Uyarı üçgeni yolu oluştur
        path = QPainterPath()
        path.moveTo(12, 2)   # Üst nokta
        path.lineTo(22, 22)  # Sağ alt
        path.lineTo(2, 22)   # Sol alt
        path.lineTo(12, 2)   # Tekrar üst nokta
        
        # Kenarlık ve dolgu renklerini ayarla
        outline_pen = QPen(QColor(255, 255, 0))  # Sarı kenarlık
        outline_pen.setWidth(2)
        painter.setPen(outline_pen)
        painter.setBrush(QBrush(QColor(255, 255, 0)))  # Sarı dolgu
        painter.drawPath(path)
        
        # Ünlem işareti çiz
        painter.setPen(QPen(QColor(0, 0, 0), 2))  # Siyah, 2px kalınlık
        painter.drawLine(QPointF(12, 8), QPointF(12, 15))  # Ünlem dikey çizgi
        painter.drawEllipse(QPointF(12, 18), 1, 1)  # Ünlem noktası
        
        painter.end()
        
        # Butona ikonu ekle
        button.setIcon(QIcon(pixmap))
        button.setIconSize(icon_size)
    
    def update_theme(self, is_dark=True):
        """Update the theme (light/dark) for all buttons and elements."""
        self.is_dark_theme = is_dark
        
        # Başlıkların rengini ayarla
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if isinstance(widget, QLabel) and widget.styleSheet().find("font-weight: bold") > -1:
                if is_dark:
                    widget.setStyleSheet("""
                        color: #FF9800;
                        font-weight: bold;
                        font-size: 16px;
                        margin: 10px 5px 5px 5px;
                        padding-left: 5px;
                        background-color: transparent;
                    """)
                else:
                    widget.setStyleSheet("""
                        color: #E65100;
                        font-weight: bold;
                        font-size: 16px;
                        margin: 10px 5px 5px 5px;
                        padding-left: 5px;
                        background-color: transparent;
                    """)
        
        # Divider'ların rengini ayarla
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if widget and widget.height() == 2:  # Divider'ların yüksekliği 2
                if is_dark:
                    widget.setStyleSheet("""
                        background-color: #666666; 
                        margin: 12px 15px;
                        border-radius: 1px;
                    """)
                else:
                    widget.setStyleSheet("""
                        background-color: #CCCCCC; 
                        margin: 12px 15px;
                        border-radius: 1px;
                    """)
        
        # Update the theme button text
        if is_dark:
            self.theme_button.setToolTip("Açık Temaya Geç")
        else:
            self.theme_button.setToolTip("Koyu Temaya Geç")
        
        # Update the theme button icon specifically
        if "dark" in self.button_icons[self.theme_button] and "light" in self.button_icons[self.theme_button]:
            theme_key = "dark" if is_dark else "light"
            icon_path = self.button_icons[self.theme_button][theme_key]
            
            if os.path.exists(icon_path):
                themed_icon = IconThemeManager.get_themed_icon(icon_path, is_dark_theme=is_dark)
                self.theme_button.setIcon(themed_icon)
        
        # Servo kontrol ikonunu güncelle
        controls_icon = self.create_controls_icon()
        self.servo_control_button.setIcon(controls_icon)
        self.button_icons[self.servo_control_button] = controls_icon
        
        # Tracking ikonunu güncelle
        tracking_icon = self.create_tracking_icon()
        self.tracking_button.setIcon(tracking_icon)
        self.button_icons[self.tracking_button] = tracking_icon
        
        # PBVS ikonunu güncelle
        pbvs_icon = self.create_pbvs_icon()
        self.pbvs_tracking_button.setIcon(pbvs_icon)
        self.button_icons[self.pbvs_tracking_button] = pbvs_icon
        
        # Update all button icons and text spacing
        for button in self.buttons:
            if button == self.theme_button or button == self.servo_control_button:  # Already handled above
                continue
                
            icon_path_or_icon = self.button_icons.get(button)
            if not icon_path_or_icon:
                continue
            
            # Özel ikonlar için QIcon nesnelerini doğrudan kullan
            if isinstance(icon_path_or_icon, QIcon):
                button.setIcon(icon_path_or_icon)
                if button in [self.servo_control_button, self.save_button]:
                    button.setIconSize(QSize(24, 24))  # Bottom buttons için daha küçük
                else:
                    button.setIconSize(QSize(28, 28))  # Diğer butonlar için orijinal boyut
            elif isinstance(icon_path_or_icon, dict):  # If it has different icons for dark/light
                icon_path = icon_path_or_icon.get("dark" if is_dark else "light", "")
                
                if os.path.exists(icon_path):
                    themed_icon = IconThemeManager.get_themed_icon(icon_path, is_dark_theme=is_dark)
                    button.setIcon(themed_icon)
                    button.setIconSize(QSize(28, 28))
            elif os.path.exists(icon_path_or_icon):
                themed_icon = IconThemeManager.get_themed_icon(icon_path_or_icon, is_dark_theme=is_dark)
                button.setIcon(themed_icon)
                if button in [self.servo_control_button, self.save_button]:
                    button.setIconSize(QSize(24, 24))
                else:
                    button.setIconSize(QSize(28, 28))
            
            # İkon ve metin arasındaki boşluğu güncelle
            text = button.text().strip()
            if text:
                # İki satır varsa her iki satırın da başında boşluk olmasını sağla
                if "\n" in text:
                    # Önce mevcut boşlukları temizle
                    lines = [line.strip() for line in text.split("\n")]
                    # Her satırın başına boşluk ekleyip birleştir
                    formatted_text = "   " + lines[0] + "\n   " + lines[1]
                    button.setText(formatted_text)
                else:
                    # Tek satırlı metin
                    button.setText("   " + text)
        
        # Update button styles
        for button in self.buttons:
            if button.isCheckable():
                if is_dark:
                    button.setStyleSheet("""
                        QPushButton {
                            text-align: left;
                            padding-left: 12px;
                            padding-right: 8px;
                            padding-top: 4px;
                            padding-bottom: 4px;
                            color: white;
                            font-size: 13px;
                            font-weight: normal;
                            min-height: 32px;
                            border-radius: 5px;
                        }
                        QPushButton:hover {
                            background-color: #444444;
                        }
                        QPushButton:checked {
                            background-color: #4CAF50;
                            color: white;
                            font-weight: bold;
                        }
                    """)
                else:
                    button.setStyleSheet("""
                        QPushButton {
                            text-align: left;
                            padding-left: 12px;
                            padding-right: 8px;
                            padding-top: 4px;
                            padding-bottom: 4px;
                            color: #333333;
                            font-size: 13px;
                            font-weight: normal;
                            min-height: 32px;
                            border-radius: 5px;
                        }
                        QPushButton:hover {
                            background-color: #e0e0e0;
                        }
                        QPushButton:checked {
                            background-color: #4CAF50;
                            color: white;
                            font-weight: bold;
                        }
                    """)
            elif button in [self.theme_button, self.settings_button, self.exit_button,
                           self.save_button, self.servo_control_button]:
                # Top and bottom icon buttons style
                if is_dark:
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #444444;
                            border-radius: 18px;
                            padding: 5px;
                            min-width: 36px;
                            min-height: 36px;
                            max-width: 36px;
                            max-height: 36px;
                        }
                        QPushButton:hover {
                            background-color: #555555;
                        }
                        QPushButton:pressed {
                            background-color: #666666;
                        }
                    """)
                else:
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #e0e0e0;
                            border-radius: 18px;
                            padding: 5px;
                            min-width: 36px;
                            min-height: 36px;
                            max-width: 36px;
                            max-height: 36px;
                        }
                        QPushButton:hover {
                            background-color: #d0d0d0;
                        }
                        QPushButton:pressed {
                            background-color: #c0c0c0;
                        }
                    """)
        
        # Update button container widgets style
        # Top buttons widget style
        self.top_buttons_widget.setStyleSheet("""
            background-color: transparent;
            border-radius: 8px;
            padding: 5px;
            margin-bottom: 10px;
        """)
        
        # Bottom buttons widget style
        self.bottom_buttons_widget.setStyleSheet("""
            background-color: transparent;
            border-radius: 8px;
            padding: 5px;
            margin-top: 10px;
        """)
        
        # Emergency stop button should stay red always
        self.emergency_stop_button.setStyleSheet("""
            QPushButton {
                background-color: #FF0000;
                color: white;
                font-weight: bold;
                font-size: 14px;
                text-align: center;
                border-radius: 5px;
                padding: 8px 8px 8px 8px;
                margin: 10px 5px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
            QPushButton:pressed {
                background-color: #AA0000;
            }
        """)
        
        # Tüm butonlar için özel temalamayı uygula (tracking butonu için de)
        self.update_all_button_icons()
        
        # Tema değişikliğinde ikonlar da güncellenmeli
        
    def update_all_button_icons(self):
        """Tüm butonların ikonlarını temalara göre günceller"""
        # Bottom buttons için icon boyutunu ayarla
        for button in [self.servo_control_button, self.save_button]:
            button.setFixedSize(36, 36)
            button.setIconSize(QSize(24, 24))
            
        # Tracking buton ikonunu güncelle
        tracking_icon = self.create_tracking_icon()
        self.tracking_button.setIcon(tracking_icon) 