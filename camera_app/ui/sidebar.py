#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sidebar Component
----------------
Reusable sidebar component for the camera application.
"""

import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor

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
        
        # Add header label
        self.header_label = QLabel("Uygulama Logları")
        self.header_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
            padding: 5px;
            margin-bottom: 5px;
        """)
        self.add_widget(self.header_label)
        
        # Create clear log button with icon - using default dark theme
        self.clear_button = QPushButton("Logları Temizle")
        icon = IconThemeManager.get_themed_icon("icons/trash.png", is_dark_theme=True)
        self.clear_button.setIcon(icon)
        self.clear_button.setIconSize(QSize(24, 24))
        self.clear_button.setStyleSheet("""
            background-color: #e74c3c;  /* Red for clear/delete action */
            text-align: left;
            padding-left: 40px;
        """)
        self.add_widget(self.clear_button)
        
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
        self.refresh_timer.start(1000)  # Refresh every second
    
    def update_text_area_style(self, is_dark=True):
        """Update the text area style based on theme."""
        if is_dark:
            self.log_text.setStyleSheet("""
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 5px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
            """)
            self.header_label.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: white;
                padding: 5px;
                margin-bottom: 5px;
            """)
            
            # Update clear button icon and text color for dark theme
            icon = IconThemeManager.get_themed_icon("icons/trash.png", is_dark_theme=True)
            self.clear_button.setIcon(icon)
            self.clear_button.setStyleSheet("""
                background-color: #e74c3c;  /* Red for clear/delete action */
                text-align: left;
                padding-left: 40px;
                color: white;
                font-weight: bold;
            """)
        else:
            self.log_text.setStyleSheet("""
                background-color: #f8f9fa;
                color: #343a40;
                border: 1px solid #ced4da;
                border-radius: 5px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
            """)
            self.header_label.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: #343a40;
                padding: 5px;
                margin-bottom: 5px;
            """)
            
            # Update clear button icon and text color for light theme
            icon = IconThemeManager.get_themed_icon("icons/trash.png", is_dark_theme=False)
            self.clear_button.setIcon(icon)
            self.clear_button.setStyleSheet("""
                background-color: #e74c3c;  /* Red for clear/delete action */
                text-align: left;
                padding-left: 40px;
                color: white;  /* White text works well on red for both themes */
                font-weight: bold;
            """)
    
    def add_log(self, message):
        """Add a log message to the text area with colorized formatting."""
        # Format the message with HTML for colorization
        formatted_html = self.format_log_message(message)
        
        # Add the formatted message
        self.log_text.append(formatted_html)
        
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
    
    def refresh_logs(self):
        """Ensure logs are displayed and updated."""
        # Force update of the text edit
        self.log_text.update()


class MenuSidebar(Sidebar):
    """Menu sidebar implementation."""
    
    def __init__(self, parent=None):
        super().__init__(parent, position="right", width=250)
        
        # Flag to track current theme
        self.is_dark_theme = True
        
        # Create menu buttons with icons
        self.theme_button = self.create_icon_button("", "icons/theme.png", icon_only=True)
        self.settings_button = self.create_icon_button("", "icons/settings.png", icon_only=True)
        self.exit_button = self.create_icon_button("", "icons/exit.png", icon_only=True)
        
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
        
        # Create a divider
        self.divider = QWidget()
        self.divider.setFixedHeight(1)
        self.divider.setStyleSheet("background-color: #555555;")
        
        # Create other menu buttons with icons and text
        self.capture_button = self.create_icon_button("Görüntü Yakala", "icons/camera.png")
        self.save_button = self.create_icon_button("Kaydet", "icons/save.png")
        self.yolo_button = self.create_icon_button("YOLO Tespiti", "icons/detection.png", checkable=True)
        self.shape_button = self.create_icon_button("Şekil Tespiti", "icons/shapes.png", checkable=True)
        self.roboflow_button = self.create_icon_button("Roboflow Tespiti", "icons/robot.png", checkable=True)
        self.fps_button = self.create_icon_button("FPS Göster", "icons/speedometer.png")
        
        # Store buttons for theme updates
        self.buttons = [
            self.theme_button, self.settings_button, self.exit_button,
            self.capture_button, self.save_button, 
            self.yolo_button, self.shape_button, self.roboflow_button,
            self.fps_button
        ]
        
        # Store icons paths and alternates for theme updates
        self.button_icons = {
            self.theme_button: {"dark": "icons/theme.png", "light": "icons/sun.png"},
            self.settings_button: "icons/settings.png",
            self.exit_button: "icons/exit.png",
            self.capture_button: "icons/camera.png",
            self.save_button: "icons/save.png",
            self.yolo_button: "icons/detection.png",
            self.shape_button: "icons/shapes.png",
            self.roboflow_button: "icons/robot.png",
            self.fps_button: "icons/speedometer.png"
        }
        
        # Add buttons to sidebar in the requested order
        self.add_widget(self.top_buttons_widget)
        self.add_widget(self.divider)
        self.add_widget(self.capture_button)
        self.add_widget(self.save_button)
        self.add_widget(self.yolo_button)
        self.add_widget(self.shape_button)
        self.add_widget(self.roboflow_button)
        self.add_widget(self.fps_button)
        self.add_stretch()
    
    def create_icon_button(self, text, icon_path, checkable=False, icon_only=False):
        """Create a button with a theme-aware icon."""
        button = QPushButton(text)
        
        # Add themed icon if exists, otherwise use a fallback text
        if os.path.exists(icon_path):
            # Create a themed icon based on current theme
            icon = IconThemeManager.get_themed_icon(icon_path, self.is_dark_theme)
            button.setIcon(icon)
            button.setIconSize(QSize(24, 24))
        else:
            # Use first letter of each word as a fallback
            fallback = ''.join([word[0] for word in text.split() if word])
            button.setText(f"[{fallback}] {text}")
        
        # Set checkable if needed
        if checkable:
            button.setCheckable(True)
            
            # Create a complete stylesheet for checkable buttons with theme-aware colors
            if self.is_dark_theme:
                button.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 40px;
                        color: white;
                    }
                    QPushButton:checked {
                        background-color: #FF5722;
                        color: white;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 40px;
                        color: #333333;
                    }
                    QPushButton:checked {
                        background-color: #FF5722;
                        color: white;
                    }
                """)
        elif icon_only:
            # Style for icon-only buttons
            if self.is_dark_theme:
                button.setStyleSheet("""
                    QPushButton {
                        text-align: center;
                        color: white;
                        min-width: 40px;
                        max-width: 40px;
                        height: 40px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #444444;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        text-align: center;
                        color: #333333;
                        min-width: 40px;
                        max-width: 40px;
                        height: 40px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #d0d0d0;
                    }
                """)
        else:
            # Simple stylesheet for non-checkable buttons with theme-aware colors
            if self.is_dark_theme:
                button.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 40px;
                        color: white;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 40px;
                        color: #333333;
                    }
                """)
        
        return button
    
    def update_theme(self, is_dark=True):
        """Update button icons and styles based on theme."""
        self.is_dark_theme = is_dark
        
        # Update button icons with the appropriate theme
        for button in self.buttons:
            if button in self.button_icons:
                if button == self.theme_button:
                    # Use different icon for theme button based on current theme
                    icon_path = self.button_icons[button]["dark" if is_dark else "light"]
                    themed_icon = IconThemeManager.get_themed_icon(icon_path, is_dark_theme=is_dark)
                else:
                    # Other buttons use regular path
                    icon_path = self.button_icons[button]
                    themed_icon = IconThemeManager.get_themed_icon(icon_path, is_dark_theme=is_dark)
                
                button.setIcon(themed_icon)
                button.setIconSize(QSize(24, 24))
        
        # Update divider color
        self.divider.setStyleSheet(f"background-color: {'#555555' if is_dark else '#cccccc'};")
        
        # Update button text colors based on theme
        for button in self.buttons:
            if button == self.theme_button or button == self.settings_button or button == self.exit_button:
                # For icon-only buttons
                if is_dark:
                    button.setStyleSheet("""
                        QPushButton {
                            text-align: center;
                            color: white;
                            min-width: 40px;
                            max-width: 40px;
                            height: 40px;
                            border-radius: 5px;
                        }
                        QPushButton:hover {
                            background-color: #444444;
                        }
                    """)
                else:
                    button.setStyleSheet("""
                        QPushButton {
                            text-align: center;
                            color: #333333;
                            min-width: 40px;
                            max-width: 40px;
                            height: 40px;
                            border-radius: 5px;
                        }
                        QPushButton:hover {
                            background-color: #d0d0d0;
                        }
                    """)
            elif button.isCheckable():
                # For checkable buttons, we need different styles
                if is_dark:
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #333333;
                            color: white;
                            text-align: left;
                            padding-left: 40px;
                        }
                        QPushButton:checked {
                            background-color: #444444;
                            border-left: 3px solid #4CAF50;
                        }
                    """)
                else:
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #e0e0e0;
                            color: black;
                            text-align: left;
                            padding-left: 40px;
                        }
                        QPushButton:checked {
                            background-color: #d0d0d0;
                            border-left: 3px solid #2196F3;
                        }
                    """)
            else:
                # For regular buttons
                if is_dark:
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #333333;
                            color: white;
                            text-align: left;
                            padding-left: 40px;
                        }
                    """)
                else:
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #e0e0e0;
                            color: black;
                            text-align: left;
                            padding-left: 40px;
                        }
                    """)
        
        # Update theme button text (no longer needed since it's icon-only) 