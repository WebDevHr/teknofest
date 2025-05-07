#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modern Camera Application with PyQt5
------------------------------------
A full-screen camera application with animated sidebars,
logging functionality, and image capture capabilities.
"""

import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from services.logger_service import LoggerService
import traceback

# utils.config modülü içinde .env dosyası zaten yükleniyor
# böylece bu dosyayı import ettiğimizde çevresel değişkenler otomatik yüklenir
from utils.config import config

def global_exception_handler(exctype, value, tb):
    logger = LoggerService()
    error_message = ''.join(traceback.format_exception(exctype, value, tb))
    logger.error(f'Global Exception: {error_message}')
    # Uygulama GUI ise kullanıcıya da göster
    try:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle('Beklenmeyen Hata')
        msg.setText('Beklenmeyen bir hata oluştu. Uygulama log dosyasını kontrol edin.')
        msg.setDetailedText(error_message)
        msg.exec_()
    except Exception:
        # Eğer GUI yoksa veya hata oluşursa, konsola yaz
        print('Beklenmeyen bir hata oluştu:', error_message)

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
    sys.excepthook = global_exception_handler
    main() 