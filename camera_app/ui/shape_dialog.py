#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Shape Detection Dialog
-------------------
Dialog for configuring shape detection parameters.
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QComboBox, QPushButton, QGroupBox, QRadioButton)
from PyQt5.QtCore import Qt

class ShapeDetectionDialog(QDialog):
    """
    Dialog for configuring shape detection parameters.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shape Detection Settings")
        self.setMinimumWidth(300)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Shape selection
        shape_group = QGroupBox("Select Shape")
        shape_layout = QVBoxLayout()
        
        self.shape_any = QRadioButton("Any Shape")
        self.shape_triangle = QRadioButton("Triangle")
        self.shape_square = QRadioButton("Square")
        self.shape_circle = QRadioButton("Circle")
        
        self.shape_any.setChecked(True)
        
        shape_layout.addWidget(self.shape_any)
        shape_layout.addWidget(self.shape_triangle)
        shape_layout.addWidget(self.shape_square)
        shape_layout.addWidget(self.shape_circle)
        
        shape_group.setLayout(shape_layout)
        layout.addWidget(shape_group)
        
        # Color selection
        color_group = QGroupBox("Select Color")
        color_layout = QVBoxLayout()
        
        self.color_any = QRadioButton("Any Color")
        self.color_red = QRadioButton("Red")
        self.color_green = QRadioButton("Green")
        self.color_blue = QRadioButton("Blue")
        
        self.color_any.setChecked(True)
        
        color_layout.addWidget(self.color_any)
        color_layout.addWidget(self.color_red)
        color_layout.addWidget(self.color_green)
        color_layout.addWidget(self.color_blue)
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_selected_shape(self):
        """Get the selected shape."""
        if self.shape_any.isChecked():
            return None
        elif self.shape_triangle.isChecked():
            return "triangle"
        elif self.shape_square.isChecked():
            return "square"
        elif self.shape_circle.isChecked():
            return "circle"
        return None
    
    def get_selected_color(self):
        """Get the selected color."""
        if self.color_any.isChecked():
            return None
        elif self.color_red.isChecked():
            return "red"
        elif self.color_green.isChecked():
            return "green"
        elif self.color_blue.isChecked():
            return "blue"
        return None 