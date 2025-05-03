#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Icon Downloader
--------------
Script to download icons for the camera application.
"""

import os
import requests
import time
from io import BytesIO
from PIL import Image

# Create icons directory if it doesn't exist
if not os.path.exists("icons"):
    os.makedirs("icons")
    print("Created icons directory")

# List of icons to download
icons = {
    "settings.png": "https://img.icons8.com/ios-filled/50/settings.png",
    "camera.png": "https://img.icons8.com/ios-filled/50/camera--v1.png",
    "save.png": "https://img.icons8.com/ios-filled/50/save.png",
    "detection.png": "https://img.icons8.com/ios-filled/50/radar.png",
    "shapes.png": "https://img.icons8.com/ios-filled/50/geometry.png",
    "robot.png": "https://img.icons8.com/ios-filled/50/robot.png",
    "speedometer.png": "https://img.icons8.com/ios-filled/50/speedometer.png",
    "theme.png": "https://img.icons8.com/ios-filled/50/day-and-night.png",
    "exit.png": "https://img.icons8.com/ios-filled/50/exit.png",
    "trash.png": "https://img.icons8.com/ios-filled/50/trash.png"
}

# Download each icon
for filename, url in icons.items():
    filepath = os.path.join("icons", filename)
    
    # Skip if file already exists
    if os.path.exists(filepath):
        print(f"Icon {filename} already exists, skipping")
        continue
    
    try:
        print(f"Downloading {filename} from {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        # Convert to PNG with transparent background if needed
        image = Image.open(BytesIO(response.content))
        
        # Save the icon
        image.save(filepath, "PNG")
        print(f"Saved {filepath}")
        
        # Sleep to avoid rate limiting
        time.sleep(0.5)
        
    except Exception as e:
        print(f"Error downloading {filename}: {e}")

print("Icon download complete!")
print("\nAttribution: Icons by Icons8 (https://icons8.com)") 