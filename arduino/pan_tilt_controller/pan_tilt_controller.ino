/*
 * Pan-Tilt Controller for IBVS Tracking with Smooth Motion
 * 
 * Controls two servos for a pan-tilt mechanism:
 * - Pan servo connected to A1
 * - Tilt servo connected to A0
 * 
 * Communication protocol via Serial:
 * - Command format: "P{pan}T{tilt}" where pan and tilt are angles (0-180)
 * - Example: "P90T45" sets pan to 90° and tilt to 45°
 * - Values can be decimal (e.g., "P90.5T45.2") for fine-grained control
 * 
 * For Teknofest project, 2025
 */

#include <Servo.h>

// Create servo objects
Servo panServo;   // Pan servo (horizontal movement)
Servo tiltServo;  // Tilt servo (vertical movement)

// Current positions (using float for more precision)
float panAngle = 90.0;
float tiltAngle = 90.0;

// Target positions (for smooth movement)
float targetPanAngle = 90.0;
float targetTiltAngle = 90.0;

// Servo limits
const float PAN_MIN = 0.0;
const float PAN_MAX = 180.0;
const float TILT_MIN = 0.0;
const float TILT_MAX = 180.0;

// For parsing commands
String inputBuffer = "";

// For smooth movement
const int MOVE_INTERVAL = 5;     // milliseconds between movements (faster updates)
const float SMOOTH_FACTOR = 0.3; // Smoothing factor (0-1.0, higher = faster movement)
unsigned long lastMoveTime = 0;

// Minimum servo step size (in degrees)
const float MIN_STEP = 0.1;      // Allow micro-adjustments

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  
  // Attach servos to Arduino pins
  panServo.attach(A1);  // Pan servo on A1
  tiltServo.attach(A0); // Tilt servo on A0
  
  // Move to center position on startup
  panServo.write(panAngle);
  tiltServo.write(tiltAngle);
  
  // Wait for servos to reach position
  delay(500);
  
  // Initial message
  Serial.println("Pan-Tilt Controller Ready");
}

void loop() {
  // Read and process serial commands
  readSerialCommands();
  
  // Update servo positions for smooth movement
  updateServos();
  
  // Small delay for stability
  delay(2);
}

void readSerialCommands() {
  // Check if data is available to read
  while (Serial.available() > 0) {
    // Read one character
    char inChar = (char)Serial.read();
    
    // If newline or carriage return, process the command
    if (inChar == '\n' || inChar == '\r') {
      if (inputBuffer.length() > 0) {
        // Process the command
        processCommand(inputBuffer);
        // Clear the buffer
        inputBuffer = "";
      }
    } else {
      // Add the character to the buffer
      inputBuffer += inChar;
    }
  }
}

void processCommand(String command) {
  // Find positions of P and T in the command
  int pIndex = command.indexOf('P');
  int tIndex = command.indexOf('T');
  
  // Check if both P and T are present
  if (pIndex >= 0 && tIndex >= 0) {
    // Extract pan value
    String panStr = command.substring(pIndex + 1, tIndex);
    // Extract tilt value (from T to the end)
    String tiltStr = command.substring(tIndex + 1);
    
    // Convert to float instead of int for more precision
    float pan = panStr.toFloat();
    float tilt = tiltStr.toFloat();
    
    // Constrain to valid ranges
    pan = constrain(pan, PAN_MIN, PAN_MAX);
    tilt = constrain(tilt, TILT_MIN, TILT_MAX);
    
    // Set target positions (actual movement happens in updateServos)
    targetPanAngle = pan;
    targetTiltAngle = tilt;
    
    // Send confirmation with decimal precision
    Serial.print("OK: P=");
    Serial.print(pan, 1);  // Show one decimal place
    Serial.print(", T=");
    Serial.println(tilt, 1);
  } 
  else {
    // Invalid command format
    Serial.print("Error: Invalid command format - ");
    Serial.println(command);
  }
}

void updateServos() {
  // Check if it's time to update servo positions
  unsigned long currentTime = millis();
  if (currentTime - lastMoveTime < MOVE_INTERVAL) {
    return;  // Not enough time has passed
  }
  lastMoveTime = currentTime;
  
  // Check if we need to move pan servo
  if (abs(panAngle - targetPanAngle) > MIN_STEP) {
    // Apply smoothing - move a percentage of the remaining distance
    float panDiff = targetPanAngle - panAngle;
    float panStep = max(MIN_STEP, abs(panDiff * SMOOTH_FACTOR)); 
    
    // Move toward target position
    if (abs(panDiff) <= panStep) {
      panAngle = targetPanAngle;  // We're close enough, go to exact position
    } else if (panDiff > 0) {
      panAngle += panStep;  // Move up
    } else {
      panAngle -= panStep;  // Move down
    }
    
    // Update servo with rounded value (servos only accept integers)
    panServo.write(round(panAngle));
  }
  
  // Check if we need to move tilt servo
  if (abs(tiltAngle - targetTiltAngle) > MIN_STEP) {
    // Apply smoothing - move a percentage of the remaining distance
    float tiltDiff = targetTiltAngle - tiltAngle;
    float tiltStep = max(MIN_STEP, abs(tiltDiff * SMOOTH_FACTOR));
    
    // Move toward target position
    if (abs(tiltDiff) <= tiltStep) {
      tiltAngle = targetTiltAngle;  // We're close enough, go to exact position
    } else if (tiltDiff > 0) {
      tiltAngle += tiltStep;  // Move right
    } else {
      tiltAngle -= tiltStep;  // Move left
    }
    
    // Update servo with rounded value (servos only accept integers)
    tiltServo.write(round(tiltAngle));
  }
} 