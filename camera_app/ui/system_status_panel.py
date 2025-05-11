#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
System Status Panel
----------------
Widget for displaying system status indicators.
"""

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                           QFrame, QSizePolicy, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor, QPalette, QPainter, QBrush, QFont

class StatusIndicator(QWidget):
    """A circular status indicator with label."""
    
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self._init_ui()

    def _init_ui(self):
        """Initialize the indicator UI using a colored QFrame for the status light."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Text label
        self.label = QLabel(self.label_text)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.label.setStyleSheet("font-weight: 500;")

        # Circular light indicator
        self.indicator = QFrame(self)
        self.indicator.setFixedSize(14, 14)
        # Initial off state (red)
        self.indicator.setStyleSheet("background-color: #FF3232; border-radius: 7px;")

        layout.addWidget(self.label)
        layout.addWidget(self.indicator)
        self.setFixedHeight(30)

    def update_status(self, status):
        """Update the indicator color based on status (green for True, red for False)."""
        color = "#00C800" if status else "#FF3232"
        self.indicator.setStyleSheet(f"background-color: {color}; border-radius: 7px;")


class SystemStatusPanel(QWidget):
    """Panel showing system status indicators."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark_theme = True  # Default to dark theme
        self.initialize()
        
    def initialize(self):
        """Initialize the status panel."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)  # Add margins around the entire panel
        main_layout.setSpacing(8)  # Spacing between header and card

        # Title - styled like log sidebar header but outside card
        self.header_label = QLabel("Sistem Durumu")
        self.header_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
            padding: 5px;
            background-color: transparent;
        """)
        self.header_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(self.header_label)

        # Create card container with margins
        self.card_container = QFrame(self)
        self.card_container.setObjectName("statusCard")
        card_layout = QVBoxLayout(self.card_container)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(6)
        
        # Content area with indicators
        self.content_widget = QWidget()
        content_layout = QHBoxLayout(self.content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)

        # Kamera
        cam_widget = QWidget()
        cam_layout = QVBoxLayout(cam_widget)
        cam_layout.setContentsMargins(0, 0, 0, 0)
        cam_layout.setSpacing(5)
        cam_label = QLabel("Kamera")
        cam_label.setAlignment(Qt.AlignCenter)
        cam_label.setStyleSheet("font-size: 10pt;")
        self.cam_circle = QFrame()
        self.cam_circle.setFixedSize(16, 16)
        self.cam_circle.setObjectName("cam_circle")
        self.cam_circle.setStyleSheet("background-color: #FF3232; border-radius: 8px;")
        cam_layout.addWidget(self.cam_circle, 0, Qt.AlignHCenter)
        cam_layout.addWidget(cam_label)
        content_layout.addWidget(cam_widget, 1, Qt.AlignCenter)

        # Arduino
        ard_widget = QWidget()
        ard_layout = QVBoxLayout(ard_widget)
        ard_layout.setContentsMargins(0, 0, 0, 0)
        ard_layout.setSpacing(5)
        ard_label = QLabel("Arduino")
        ard_label.setAlignment(Qt.AlignCenter)
        ard_label.setStyleSheet("font-size: 10pt;")
        self.ard_circle = QFrame()
        self.ard_circle.setFixedSize(16, 16)
        self.ard_circle.setObjectName("ard_circle")
        self.ard_circle.setStyleSheet("background-color: #FF3232; border-radius: 8px;")
        ard_layout.addWidget(self.ard_circle, 0, Qt.AlignHCenter)
        ard_layout.addWidget(ard_label)
        content_layout.addWidget(ard_widget, 1, Qt.AlignCenter)

        # Silah
        wea_widget = QWidget()
        wea_layout = QVBoxLayout(wea_widget)
        wea_layout.setContentsMargins(0, 0, 0, 0)
        wea_layout.setSpacing(5)
        wea_label = QLabel("Silah")
        wea_label.setAlignment(Qt.AlignCenter)
        wea_label.setStyleSheet("font-size: 10pt;")
        self.wea_circle = QFrame()
        self.wea_circle.setFixedSize(16, 16)
        self.wea_circle.setObjectName("wea_circle")
        self.wea_circle.setStyleSheet("background-color: #FF3232; border-radius: 8px;")
        wea_layout.addWidget(self.wea_circle, 0, Qt.AlignHCenter)
        wea_layout.addWidget(wea_label)
        content_layout.addWidget(wea_widget, 1, Qt.AlignCenter)

        # Add content to card
        card_layout.addWidget(self.content_widget)
        
        # Add card to main layout with margins
        main_layout.addWidget(self.card_container)

        # Allow panel to expand horizontally with sidebar
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Apply initial styling
        self.update_theme(self.is_dark_theme)

    def update_theme(self, is_dark=True):
        """Update the theme (light/dark) for all elements."""
        self.is_dark_theme = is_dark
        
        if is_dark:
            self.header_label.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: white;
                padding: 5px;
                background-color: transparent;
            """)
            # Match the log panel card style exactly
            self.card_container.setStyleSheet("""
                #statusCard {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                    border: 1px solid #34495e;
                    border-radius: 5px;
                    margin: 5px;
                }
                QLabel {
                    color: #ecf0f1;
                }
            """)
            self.content_widget.setStyleSheet("background-color: transparent;")
        else:
            self.header_label.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: #343a40;
                padding: 5px;
                background-color: transparent;
            """)
            # Light theme card style
            self.card_container.setStyleSheet("""
                #statusCard {
                    background-color: #f8f9fa;
                    color: #343a40;
                    border: 1px solid #ced4da;
                    border-radius: 5px;
                    margin: 5px;
                }
                QLabel {
                    color: #343a40;
                }
            """)
            self.content_widget.setStyleSheet("background-color: transparent;")

    @pyqtSlot(bool)
    def updateCameraStatus(self, status):
        """Update camera status."""
        color = '#00C800' if status else '#FF3232'
        self.cam_circle.setStyleSheet(f"background-color: {color}; border-radius: 8px;")

    @pyqtSlot(bool)
    def updateArduinoStatus(self, status):
        """Update Arduino connection status."""
        color = '#00C800' if status else '#FF3232'
        self.ard_circle.setStyleSheet(f"background-color: {color}; border-radius: 8px;")

    @pyqtSlot(bool)
    def updateWeaponStatus(self, status):
        """Update weapon status."""
        color = '#00C800' if status else '#FF3232'
        self.wea_circle.setStyleSheet(f"background-color: {color}; border-radius: 8px;")
    
    # Keep these methods for backward compatibility
    @pyqtSlot(bool)
    def updateDetectorStatus(self, status):
        """Legacy method for backward compatibility."""
        pass
    
    @pyqtSlot(bool)
    def updateTrackingStatus(self, status):
        """Legacy method for backward compatibility."""
        pass 