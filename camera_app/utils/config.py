#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration Utilities
---------------------
Configuration settings for the application.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Proje kök dizini - Bu kodun iki seviye üzerindedir (utils -> camera_app -> kök)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# camera_app dizini
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# .env dosyasını camera_app klasörü altında yükle
env_path = Path(APP_DIR) / '.env'
load_dotenv(dotenv_path=env_path)

# Alt dizinleri tanımla
DEFAULT_DATA_DIR = os.path.join(ROOT_DIR, 'data')
DEFAULT_MODELS_DIR = os.path.join(APP_DIR, 'models')

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
        self.camera_id = int(os.getenv('CAMERA_ID', 0))
        self.camera_fps = int(os.getenv('CAMERA_FPS', 30))
        self.camera_width = int(os.getenv('CAMERA_WIDTH', 640))
        self.camera_height = int(os.getenv('CAMERA_HEIGHT', 480))
        self.save_format = os.getenv('SAVE_FORMAT', 'JPEG')
        
        # Camera additional options
        self.auto_exposure = os.getenv('AUTO_EXPOSURE', 'True').lower() in ('true', '1', 't')
        self.auto_white_balance = os.getenv('AUTO_WHITE_BALANCE', 'True').lower() in ('true', '1', 't')
        
        # UI settings
        self.theme = "dark"
        self.log_sidebar_width = 300
        self.menu_sidebar_width = 250
        
        # Yol ayarları
        # Data dizini (logs, captures, etc.)
        self.data_dir = os.getenv('DATA_DIR', DEFAULT_DATA_DIR)
        
        # Alt dizinler
        self.logs_dir = os.path.join(self.data_dir, 'logs')
        self.captures_dir = os.path.join(self.data_dir, 'captures')
        
        # Model dizini ve model dosyaları 
        self.model_dir = os.getenv('MODEL_DIR', DEFAULT_MODELS_DIR)
        
        # Model dosya adları
        self.balloon_model = os.getenv('BALLOON_MODEL', 'bests_balloon_30_dark.pt')
        self.engagement_model = os.getenv('ENGAGEMENT_MODEL', 'engagement-best.pt')
        self.friend_foe_model = os.getenv('FRIEND_FOE_MODEL', 'friend_foe(v8n).pt')
        self.balloon_classic_model = os.getenv('BALLOON_CLASSIC_MODEL', 'bestv8m_100_640.pt')
        self.engagement_shape_model = os.getenv('ENGAGEMENT_SHAPE_MODEL', 'engagement-shape.pt')
        
        # Pan-Tilt servo bağlantı ayarları
        self.pan_tilt_serial_port = os.getenv('PAN_TILT_SERIAL_PORT', 'COM8')
        self.pan_tilt_baud_rate = int(os.getenv('PAN_TILT_BAUD_RATE', 115200))
        
        # Pan-Tilt servo merkez pozisyon ayarları
        self.pan_center = int(os.getenv('PAN_CENTER', 90))
        self.tilt_center = int(os.getenv('TILT_CENTER', 90))
        
        # Pan-Tilt servo açı sınırları
        self.pan_min_angle = int(os.getenv('PAN_MIN_ANGLE', 0))
        self.pan_max_angle = int(os.getenv('PAN_MAX_ANGLE', 180))
        self.tilt_min_angle = int(os.getenv('TILT_MIN_ANGLE', 0))
        self.tilt_max_angle = int(os.getenv('TILT_MAX_ANGLE', 180))
        
        # Diğer ayarlar
        self.use_gpu = os.getenv('USE_GPU', 'True').lower() in ('true', '1', 't')
    
    def get(self, key, default=None):
        """Get a configuration value."""
        return getattr(self, key, default)
    
    def set(self, key, value):
        """Set a configuration value."""
        setattr(self, key, value)
    
    def ensure_dirs_exist(self):
        """Ensure that all required directories exist."""
        # Ana veri dizinini oluştur
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Alt dizinleri oluştur
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.captures_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
        
        return True
        
    def get_model_dir(self):
        """Get the model directory"""
        if not os.path.exists(self.model_dir):
            print(f"Warning: Model directory {self.model_dir} not found. Using default: {DEFAULT_MODELS_DIR}")
            return DEFAULT_MODELS_DIR
        return self.model_dir
    
    def get_model_path(self, model_name):
        """Get the full path of a model file."""
        model_dir = self.get_model_dir()
        model_path = os.path.join(model_dir, model_name)
        
        # If model doesn't exist, look for it in the default directory
        if not os.path.exists(model_path):
            default_path = os.path.join(DEFAULT_MODELS_DIR, model_name)
            if os.path.exists(default_path):
                return default_path
            else:
                print(f"Warning: Model {model_name} not found in {model_dir} or {DEFAULT_MODELS_DIR}")
                return None
        
        return model_path
    
    def get_balloon_model_path(self):
        """Get path to balloon detection model."""
        return self.get_model_path(self.balloon_model)
    
    def get_engagement_model_path(self):
        """Get path to engagement model."""
        return self.get_model_path(self.engagement_model)
    
    def get_friend_foe_model_path(self):
        """Get path to friend/foe model."""
        return self.get_model_path(self.friend_foe_model)
    
    def get_balloon_classic_model_path(self):
        """Get path to balloon classic model."""
        return self.get_model_path(self.balloon_classic_model)
    
    def get_engagement_shape_model_path(self):
        """Get path to engagement shape model."""
        return self.get_model_path(self.engagement_shape_model)

# Create a singleton instance for easy import
config = Config() 