#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modern Camera Application with PyQt5
------------------------------------
A full-screen camera application with animated sidebars,
logging functionality, and image capture capabilities.
"""

import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from services.logger_service import LoggerService

# utils.config modülü içinde .env dosyası zaten yükleniyor
# böylece bu dosyayı import ettiğimizde çevresel değişkenler otomatik yüklenir
from utils.config import config

def main():
    # Initialize application
    app = QApplication(sys.argv)
    
    # Gerekli dizinlerin varlığını kontrol et ve oluştur
    # Bu merkezi bir fonksiyon sayesinde tüm dizinleri bir yerden yönetiyoruz
    config.ensure_dirs_exist()
    
    # Initialize logger service (singleton)
    logger = LoggerService()
    logger.info("Uygulama başlatıldı")
    
    # Create and show main window
    window = MainWindow()
    
    # Start application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 