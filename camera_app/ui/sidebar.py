#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sidebar Component
----------------
Reusable sidebar component for the camera application.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal

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
        super().__init__(parent, position="left", width=300)
        
        # Create clear log button
        self.clear_button = QPushButton("Clear Log")
        self.add_widget(self.clear_button)
        
        # Create log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.add_widget(self.log_text)
    
    def add_log(self, message):
        """Add a log message to the text area."""
        self.log_text.append(message)
        
        # Auto-scroll to the bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_logs(self):
        """Clear the log text area."""
        self.log_text.clear()


class MenuSidebar(Sidebar):
    """Menu sidebar implementation."""
    
    def __init__(self, parent=None):
        super().__init__(parent, position="right", width=250)
        
        # Create menu buttons
        self.settings_button = QPushButton("Settings")
        self.capture_button = QPushButton("Capture")
        self.save_button = QPushButton("Save")
        self.yolo_button = QPushButton("YOLO Detection")
        self.shape_button = QPushButton("Shape Detection")
        self.roboflow_button = QPushButton("Roboflow Detection")
        self.exit_button = QPushButton("Exit")
        
        # Set toggle button style for detection buttons
        self.yolo_button.setCheckable(True)
        self.yolo_button.setStyleSheet("""
            QPushButton:checked {
                background-color: #FF5722;
            }
        """)
        
        self.shape_button.setCheckable(True)
        self.shape_button.setStyleSheet("""
            QPushButton:checked {
                background-color: #FF5722;
            }
        """)
        
        self.roboflow_button.setCheckable(True)
        self.roboflow_button.setStyleSheet("""
            QPushButton:checked {
                background-color: #FF5722;
            }
        """)
        
        # Add buttons to sidebar
        self.add_widget(self.settings_button)
        self.add_widget(self.capture_button)
        self.add_widget(self.save_button)
        self.add_widget(self.yolo_button)
        self.add_widget(self.shape_button)
        self.add_widget(self.roboflow_button)
        self.add_widget(self.exit_button)
        self.add_stretch() 