#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Icon Downloader
--------------
Download icons for the camera application.
"""

import os
import requests
from pathlib import Path

# Create icons directory if it doesn't exist
os.makedirs('icons', exist_ok=True)

# Define icons to download with their URLs
icons = {
    # Camera menu icons
    'settings.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/settings.svg',
    'camera.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/camera.svg',
    'save.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/save.svg',
    'detection.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/target.svg',
    'shapes.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/triangle.svg',
    'robot.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/cpu.svg',
    'speedometer.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/activity.svg',
    'theme.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/moon.svg',
    'sun.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/sun.svg',
    'exit.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/log-out.svg',
    'trash.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/trash-2.svg',
    
    # Additional icons for main window buttons
    'fullscreen.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/maximize.svg',
    'minimize.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/minimize.svg',
    'menu.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/menu.svg',
    'log.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/list.svg',
    
    # New arrow icons for sidebar toggle buttons
    'arrow-left.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/chevron-left.svg',
    'arrow-right.png': 'https://raw.githubusercontent.com/feathericons/feather/master/icons/chevron-right.svg',
}

# Download each icon
success_count = 0
failed_icons = []

for filename, url in icons.items():
    file_path = Path('icons') / filename
    
    # Skip if file already exists
    if file_path.exists():
        print(f"✓ {filename} already exists, skipping.")
        success_count += 1
        continue
    
    try:
        # Download the SVG file
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise exception if request failed
        
        # Save the file
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✓ Downloaded {filename}")
        success_count += 1
    except Exception as e:
        print(f"✗ Failed to download {filename}: {str(e)}")
        failed_icons.append(filename)

# Print summary
print(f"\nDownload summary: {success_count}/{len(icons)} icons downloaded successfully.")
if failed_icons:
    print(f"Failed icons: {', '.join(failed_icons)}")
else:
    print("All icons were downloaded successfully!") 