#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kalman Filter Service
---------------------
Service for tracking objects and compensating for camera/processing delay using Kalman filtering.
"""

import numpy as np
import cv2
import time
from collections import defaultdict
from PyQt5.QtCore import QObject, pyqtSignal
from services.logger_service import LoggerService

class KalmanFilterService(QObject):
    """
    Service for tracking objects and compensating for camera/processing delay using Kalman filtering.
    """
    
    # Signals
    filter_updated = pyqtSignal(dict)  # Signal with updated predictions
    
    def __init__(self):
        super().__init__()
        self.logger = LoggerService()
        
        # Dictionary to store Kalman filter for each track ID
        self.kalman_filters = {}
        
        # Dictionary to store timing info for delay estimation
        self.timestamps = {}
        self.processing_delays = []
        self.max_delay_samples = 30  # Store last 30 samples for delay calculation
        
        # Average camera and processing delay (in seconds)
        self.avg_camera_delay = 0.0
        self.avg_processing_delay = 0.0
        
        # Flag to indicate if delay calibration is complete
        self.is_calibrated = False
        
        # Initialize with estimates
        self.avg_camera_delay = 0.05  # Initial estimate: 50ms camera delay
        self.avg_processing_delay = 0.1  # Initial estimate: 100ms processing delay
        self.total_delay = self.avg_camera_delay + self.avg_processing_delay
        
        # Kalman filter parameters
        self.dt = 1.0  # Time step (will be calculated based on actual frame times)
        
        self.logger.info("Kalman Filter Service initialized")
    
    def mark_frame_received(self, frame_id=None):
        """
        Mark the time when a frame is received from the camera.
        
        Args:
            frame_id: Optional identifier for the frame
        """
        if frame_id is None:
            frame_id = time.time()  # Use current time as frame ID if not provided
        
        self.timestamps[frame_id] = {
            'received': time.time(),
            'processing_start': None,
            'processing_end': None
        }
        return frame_id
    
    def mark_processing_start(self, frame_id):
        """
        Mark the time when processing starts for a frame.
        
        Args:
            frame_id: Frame identifier
        """
        if frame_id in self.timestamps:
            self.timestamps[frame_id]['processing_start'] = time.time()
        else:
            self.logger.warning(f"Unknown frame_id in mark_processing_start: {frame_id}")
    
    def mark_processing_end(self, frame_id):
        """
        Mark the time when processing ends for a frame and update delay estimates.
        
        Args:
            frame_id: Frame identifier
        """
        if frame_id in self.timestamps:
            self.timestamps[frame_id]['processing_end'] = time.time()
            
            # Calculate processing delay for this frame
            if self.timestamps[frame_id]['processing_start'] is not None:
                start = self.timestamps[frame_id]['processing_start']
                end = self.timestamps[frame_id]['processing_end']
                delay = end - start
                
                # Update processing delay list
                self.processing_delays.append(delay)
                if len(self.processing_delays) > self.max_delay_samples:
                    self.processing_delays.pop(0)
                
                # Update average processing delay
                self.avg_processing_delay = np.mean(self.processing_delays)
                
                # Update total delay
                self.total_delay = self.avg_camera_delay + self.avg_processing_delay
                
                # Mark as calibrated after enough samples
                if len(self.processing_delays) >= 10 and not self.is_calibrated:
                    self.is_calibrated = True
                    self.logger.info("Delay calibration complete")
        else:
            self.logger.warning(f"Unknown frame_id in mark_processing_end: {frame_id}")
    
    def initialize_kalman(self, track_id, frame_center=None):
        """Initialize a Kalman filter for a new track."""
        # Create Kalman filter
        kalman = cv2.KalmanFilter(4, 2)  # 4 state variables (x,y,dx,dy), 2 measurements (x,y)
        
        # State transition matrix (describes physics: position + velocity)
        kalman.transitionMatrix = np.array([
            [1, 0, self.dt, 0],   # x = x + dt*dx
            [0, 1, 0, self.dt],   # y = y + dt*dy
            [0, 0, 1, 0],         # dx = dx
            [0, 0, 0, 1]          # dy = dy
        ], np.float32)
        
        # Initialize measurement matrix (we measure only x,y locations)
        kalman.measurementMatrix = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], np.float32)
        
        # Process noise covariance matrix - daha düşük değerler ilk tahminin daha stabil olmasını sağlar
        # İlk tahminlerde hareketin az olması için düşük process noise kullanıyoruz
        kalman.processNoiseCov = np.array([
            [0.001, 0, 0, 0],     # x pozisyon process noise (düşürüldü)
            [0, 0.001, 0, 0],     # y pozisyon process noise (düşürüldü)
            [0, 0, 0.01, 0],      # dx hız process noise (düşürüldü)
            [0, 0, 0, 0.01]       # dy hız process noise (düşürüldü)
        ], np.float32)
        
        # Measurement noise covariance matrix - düşük değerler ölçümlere daha çok güvenileceğini gösterir
        kalman.measurementNoiseCov = np.array([
            [0.1, 0],
            [0, 0.1]
        ], np.float32)
        
        # Error covariance matrix - düşük değerler başlangıçtaki belirsizliğin az olduğunu gösterir
        kalman.errorCovPost = np.array([
            [0.01, 0, 0, 0],     # x pozisyon hatası (düşürüldü)
            [0, 0.01, 0, 0],     # y pozisyon hatası (düşürüldü)
            [0, 0, 0.01, 0],     # dx hız hatası (düşürüldü)
            [0, 0, 0, 0.01]      # dy hız hatası (düşürüldü)
        ], np.float32)
        
        # Initialize position for track
        center_pos = None
        
        # Initialize state from frame center instead of default (0,0)
        if frame_center is not None:
            # Initialize state with position at frame center and zero velocity
            kalman.statePost = np.array([
                [frame_center[0]],  # x position (frame center x)
                [frame_center[1]],  # y position (frame center y)
                [0],                # dx (zero initial velocity)
                [0]                 # dy (zero initial velocity)
            ], np.float32)
            
            # statePredict'i de merkez olarak ayarlayarak ilk tahminin kaymasını önle
            kalman.statePre = np.array([
                [frame_center[0]],  # x position (frame center x)
                [frame_center[1]],  # y position (frame center y)
                [0],                # dx (zero initial velocity)
                [0]                 # dy (zero initial velocity)
            ], np.float32)
            
            center_pos = frame_center
        else:
            # Use default initial state with centered position
            # Try to estimate a default center (HD resolution)
            default_center_x = 640  # Half of 1280 (typical HD width)
            default_center_y = 360  # Half of 720 (typical HD height)
            
            kalman.statePost = np.array([
                [default_center_x],  # x position at estimated center
                [default_center_y],  # y position at estimated center
                [0],                # dx (zero initial velocity)
                [0]                 # dy (zero initial velocity)
            ], np.float32)
            
            # statePredict'i de merkez olarak ayarla
            kalman.statePre = np.array([
                [default_center_x],  # x position at estimated center
                [default_center_y],  # y position at estimated center
                [0],                # dx (zero initial velocity)
                [0]                 # dy (zero initial velocity)
            ], np.float32)
            
            center_pos = (default_center_x, default_center_y)
        
        # Pre-fill history and prediction history with center position
        # so the visualization starts from the center instead of empty
        initial_history = [(center_pos[0], center_pos[1]) for _ in range(3)]
        
        # Save to dictionary
        self.kalman_filters[track_id] = {
            'filter': kalman,
            'last_update': time.time(),
            'history': initial_history.copy(),  # Initialize history with center position
            'prediction_history': initial_history.copy(),  # Initialize prediction history with center position
            'stable_count': 0  # İlk birkaç tahminin daha stabil olması için sayaç
        }
    
    def update(self, track_id, measurement, frame_time=None, frame_center=None):
        """
        Update the Kalman filter with a new measurement.
        
        Args:
            track_id: ID of the track to update
            measurement: (x, y) position of the detection
            frame_time: Optional timestamp of the frame
            frame_center: Optional (x, y) center of the frame for new track initialization
            
        Returns:
            Corrected position (x, y) after Kalman update
        """
        # Initialize if this is a new track
        if track_id not in self.kalman_filters:
            self.initialize_kalman(track_id, frame_center)
        
        current_time = time.time()
        
        # Update dt for this track based on time since last update
        if frame_time is None:
            # If frame_time is not provided, use the time since last update
            time_delta = current_time - self.kalman_filters[track_id]['last_update']
            self.dt = max(0.01, min(0.5, time_delta))  # Limit dt between 10ms and 500ms
        else:
            # If frame_time is provided, use it to calculate dt
            if 'last_frame_time' in self.kalman_filters[track_id]:
                self.dt = frame_time - self.kalman_filters[track_id]['last_frame_time']
            else:
                self.dt = 0.033  # Default to ~30 FPS if no previous frame time
            self.kalman_filters[track_id]['last_frame_time'] = frame_time
        
        # Update transition matrix with current dt
        kalman = self.kalman_filters[track_id]['filter']
        kalman.transitionMatrix[0, 2] = self.dt
        kalman.transitionMatrix[1, 3] = self.dt
        
        # Convert measurement to proper format
        measurement = np.array([[measurement[0]], [measurement[1]]], dtype=np.float32)
        
        # Record the measurement time
        self.kalman_filters[track_id]['last_update'] = current_time
        
        # Update Kalman filter with the measurement
        kalman.correct(measurement)
        
        # Store measurement in history
        self.kalman_filters[track_id]['history'].append((measurement[0][0], measurement[1][0]))
        if len(self.kalman_filters[track_id]['history']) > 30:
            self.kalman_filters[track_id]['history'].pop(0)
        
        # Get corrected position
        corrected = kalman.statePost
        return (corrected[0][0], corrected[1][0])
    
    def predict(self, track_id, time_offset=None, frame_center=None):
        """
        Predict position at a future time offset.
        
        Args:
            track_id: ID of the track to predict
            time_offset: Time in future to predict for (if None, uses total system delay)
            frame_center: Optional center of frame to return for first prediction
            
        Returns:
            Predicted position (x, y)
        """
        if track_id not in self.kalman_filters:
            # If frame center is provided, return that for missing tracks
            if frame_center is not None:
                return frame_center
            return None
        
        # Use total delay if time_offset not specified
        if time_offset is None:
            time_offset = self.total_delay
        
        # Get Kalman filter for this track
        kalman = self.kalman_filters[track_id]['filter']
        track_data = self.kalman_filters[track_id]
        
        # İlk 5 tahmin için stabiliteyi arttır
        stable_threshold = 5
        if track_data['stable_count'] < stable_threshold and frame_center is not None:
            track_data['stable_count'] += 1
            
            # İlk birkaç tahminde, merkeze doğru çeken bir etki uygulayalım
            # Stabilite sayacı arttıkça merkezin etkisi azalır
            stabilization_factor = 1.0 - (track_data['stable_count'] / stable_threshold)
            
            # Geçişi yumuşatmak için doğrusal interpolasyon kullanıyoruz
            center_weight = 0.8 * stabilization_factor  # Başta %80 merkez etkisi, giderek azalır
            
            # Check if this is the first prediction (no history yet)
            prediction_history = track_data['prediction_history']
            if len(prediction_history) == 0:
                # For first prediction, just return the frame center as prediction
                predicted_pos = frame_center
                # Store prediction in history
                prediction_history.append(predicted_pos)
                return predicted_pos
                
            # Kalman tahminini al
            # Store current state to restore later
            current_state = kalman.statePost.copy()
            current_transition = kalman.transitionMatrix.copy()
            
            # Set transition matrix for prediction with time_offset
            predict_transition = kalman.transitionMatrix.copy()
            predict_transition[0, 2] = time_offset
            predict_transition[1, 3] = time_offset
            kalman.transitionMatrix = predict_transition
            
            # Predict
            prediction = kalman.predict()
            
            # Restore original state
            kalman.statePost = current_state
            kalman.transitionMatrix = current_transition
            
            # Convert prediction to (x, y) coordinates
            kalman_pos = (prediction[0][0], prediction[1][0])
            
            # İlk birkaç tahminde merkez ile kalman tahmini arasında interpolasyon yap
            predicted_pos = (
                kalman_pos[0] * (1 - center_weight) + frame_center[0] * center_weight,
                kalman_pos[1] * (1 - center_weight) + frame_center[1] * center_weight
            )
        else:
            # Normal prediction for stable tracks
            # Check if this is the first prediction (no history yet)
            prediction_history = track_data['prediction_history']
            if len(prediction_history) == 0 and frame_center is not None:
                # For first prediction, just return the frame center as prediction
                predicted_pos = frame_center
                # Store prediction in history
                prediction_history.append(predicted_pos)
                return predicted_pos
            
            # Store current state to restore later
            current_state = kalman.statePost.copy()
            current_transition = kalman.transitionMatrix.copy()
            
            # Set transition matrix for prediction with time_offset
            predict_transition = kalman.transitionMatrix.copy()
            predict_transition[0, 2] = time_offset
            predict_transition[1, 3] = time_offset
            kalman.transitionMatrix = predict_transition
            
            # Predict
            prediction = kalman.predict()
            
            # Restore original state
            kalman.statePost = current_state
            kalman.transitionMatrix = current_transition
            
            # Convert prediction to (x, y) coordinates
            predicted_pos = (prediction[0][0], prediction[1][0])
        
        # Store prediction in history
        prediction_history.append(predicted_pos)
        if len(prediction_history) > 30:
            prediction_history.pop(0)
        
        return predicted_pos
    
    def get_all_predictions(self):
        """
        Get predictions for all tracked objects.
        
        Returns:
            Dictionary of track_id -> predicted_position
        """
        predictions = {}
        for track_id in self.kalman_filters:
            predictions[track_id] = self.predict(track_id)
        return predictions
    
    def remove_track(self, track_id):
        """
        Remove a track from the tracking system.
        
        Args:
            track_id: ID of the track to remove
        """
        if track_id in self.kalman_filters:
            del self.kalman_filters[track_id]
    
    def draw_debug(self, frame, predictions=None, show_history=True):
        """
        Draw debug visualization for Kalman predictions.
        
        Args:
            frame: The image to draw on
            predictions: Optional dictionary of track_id -> predicted_position
            show_history: Whether to show the history of positions
            
        Returns:
            Frame with debug visualization
        """
        # Calculate frame center
        height, width = frame.shape[:2]
        frame_center = (width // 2, height // 2)
        
        if predictions is None:
            predictions = {}
            for track_id in self.kalman_filters:
                predictions[track_id] = self.predict(track_id, None, frame_center)
        
        # Create a copy to draw on
        vis_frame = frame.copy()
        
        # Önce kılavuz çizgi çiz - ekranın merkezi ile tahminler arasında
        for track_id, predicted_pos in predictions.items():
            if predicted_pos is None:
                continue
                
            # Çizgiyi merkezden tahmine doğru çiz (hedef gösterici gibi)
            cv2.line(vis_frame, 
                    (int(frame_center[0]), int(frame_center[1])),
                    (int(predicted_pos[0]), int(predicted_pos[1])),
                    (0, 255, 255), 1, cv2.LINE_AA)  # Sarı çizgi, anti-aliased
        
        # Draw for each track
        for track_id, predicted_pos in predictions.items():
            if predicted_pos is None:
                continue
                
            # Draw current position
            if track_id in self.kalman_filters:
                history = self.kalman_filters[track_id]['history']
                if history:
                    # Get the most recent actual position
                    current_pos = history[-1]
                    cv2.circle(vis_frame, (int(current_pos[0]), int(current_pos[1])), 
                            5, (0, 255, 0), 2)  # Green circle for current position
            
            # Draw predicted position
            cv2.circle(vis_frame, (int(predicted_pos[0]), int(predicted_pos[1])), 
                    7, (255, 0, 0), 2)  # Blue circle for prediction
            
            # Draw text for predicted position
            cv2.putText(vis_frame, f"P{track_id}", 
                    (int(predicted_pos[0]) + 10, int(predicted_pos[1]) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            # Draw history if requested
            if show_history and track_id in self.kalman_filters:
                history = self.kalman_filters[track_id]['history']
                pred_history = self.kalman_filters[track_id]['prediction_history']
                
                # Draw actual path
                if len(history) > 1:
                    for i in range(1, len(history)):
                        pt1 = (int(history[i-1][0]), int(history[i-1][1]))
                        pt2 = (int(history[i][0]), int(history[i][1]))
                        cv2.line(vis_frame, pt1, pt2, (0, 255, 0), 1)  # Green line for actual path
                
                # Draw predicted path - daha ince ve daha düzgün
                if len(pred_history) > 1:
                    points = np.array(pred_history, dtype=np.int32).reshape((-1, 1, 2))
                    cv2.polylines(vis_frame, [points], False, (255, 0, 0), 1, cv2.LINE_AA)  # Anti-aliased blue line
        
        # Add delay information text - sarı renkte gösterelim (daha görünür olması için)
        cv2.putText(vis_frame, f"Processing: {self.avg_processing_delay*1000:.1f}ms", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(vis_frame, f"Camera: {self.avg_camera_delay*1000:.1f}ms", 
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(vis_frame, f"Total Delay: {self.total_delay*1000:.1f}ms", 
                (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        return vis_frame
    
    def cleanup_old_tracks(self, max_age_seconds=2.0):
        """
        Remove tracks that haven't been updated recently.
        
        Args:
            max_age_seconds: Maximum time in seconds since last update
        """
        current_time = time.time()
        tracks_to_remove = []
        
        # Identify old tracks
        for track_id, track_data in self.kalman_filters.items():
            if current_time - track_data['last_update'] > max_age_seconds:
                tracks_to_remove.append(track_id)
                
        # Remove identified tracks
        for track_id in tracks_to_remove:
            self.remove_track(track_id)
            
        return len(tracks_to_remove) 