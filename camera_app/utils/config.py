#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration Utilities
---------------------
Configuration settings for the application.
"""

class Config:
    """
    Configuration settings for the application.
    Implements the Singleton pattern.
    """
    # Singleton instance
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize default configuration."""
        # Application settings
        self.app_name = "Modern Camera App"
        self.app_version = "1.0.0"
        
        # Camera settings
        self.camera_id = 0
        self.camera_fps = 30
        
        # UI settings
        self.theme = "dark"
        self.log_sidebar_width = 300
        self.menu_sidebar_width = 250
        
        # File paths
        self.captures_dir = "captures"
        self.logs_dir = "logs"
    
    def get(self, key, default=None):
        """Get a configuration value."""
        return getattr(self, key, default)
    
    def set(self, key, value):
        """Set a configuration value."""
        setattr(self, key, value) 