#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logger Service
-------------
Singleton service for logging application events.
"""

import os
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

class LoggerService(QObject):
    """
    Singleton Logger Service for application-wide logging.
    Implements the Singleton pattern.
    """
    # Singleton instance
    _instance = None
    
    # Signal emitted when a new log message is added
    log_added = pyqtSignal(str)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the logger service."""
        super().__init__()
        self.logs = []
        self.log_file = None
        
        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")
            
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"logs/app_log_{timestamp}.txt"
        
        # Write header to log file
        with open(self.log_file, "w") as f:
            f.write(f"=== Camera App Log - Started at {timestamp} ===\n\n")
    
    def _format_message(self, level, message):
        """Format a log message with timestamp and level."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"{timestamp} [{level}]: {message}"
    
    def _write_to_file(self, formatted_message):
        """Write a log message to the log file."""
        with open(self.log_file, "a") as f:
            f.write(formatted_message + "\n")
    
    def log(self, level, message):
        """Log a message with the specified level."""
        formatted_message = self._format_message(level, message)
        self.logs.append(formatted_message)
        self._write_to_file(formatted_message)
        self.log_added.emit(formatted_message)
        return formatted_message
    
    def info(self, message):
        """Log an info message."""
        return self.log("INFO", message)
    
    def warning(self, message):
        """Log a warning message."""
        return self.log("WARNING", message)
    
    def error(self, message):
        """Log an error message."""
        return self.log("ERROR", message)
    
    def clear(self):
        """Clear the in-memory logs."""
        self.logs = []
        self.log("INFO", "Logs cleared")
        
    def get_logs(self):
        """Get all logs."""
        return self.logs 