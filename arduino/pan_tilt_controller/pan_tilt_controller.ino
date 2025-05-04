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
 * 
 * For Teknofest project, 2025
 */

#include <Servo.h>

// Create servo objects
Servo panServo;   // Pan servo (horizontal movement)
Servo tiltServo;  // Tilt servo (vertical movement)

// Current positions
int panAngle = 90;
int tiltAngle = 90;

// Target positions (for smooth movement)
int targetPanAngle = 90;
int targetTiltAngle = 90;

// Servo limits
const int PAN_MIN = 0;
const int PAN_MAX = 180;
const int TILT_MIN = 0;
const int TILT_MAX = 180;

// For parsing commands
String inputBuffer = "";

// For smooth movement
const int MOVE_INTERVAL = 10;   // milliseconds between movements (daha hızlı güncellemeler)
const float SMOOTH_FACTOR = 0.4; // Smoothing factor (0-1.0, daha yüksek = daha hızlı hareket)
unsigned long lastMoveTime = 0;

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
  delay(5);
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
    
    // Convert to integers
    int pan = panStr.toInt();
    int tilt = tiltStr.toInt();
    
    // Constrain to valid ranges
    pan = constrain(pan, PAN_MIN, PAN_MAX);
    tilt = constrain(tilt, TILT_MIN, TILT_MAX);
    
    // Set target positions (actual movement happens in updateServos)
    targetPanAngle = pan;
    targetTiltAngle = tilt;
    
    // Send confirmation
    Serial.print("OK: P=");
    Serial.print(pan);
    Serial.print(", T=");
    Serial.println(tilt);
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
  if (panAngle != targetPanAngle) {
    // Apply smoothing - move a percentage of the remaining distance
    float panDiff = targetPanAngle - panAngle;
    int panStep = max(1, (int)(panDiff * SMOOTH_FACTOR)); 
    
    // Move toward target position
    if (abs(panDiff) <= abs(panStep)) {
      panAngle = targetPanAngle;  // We're close enough, go to exact position
    } else if (panDiff > 0) {
      panAngle += panStep;  // Move up
    } else {
      panAngle -= panStep;  // Move down
    }
    
    // Update servo
    panServo.write(panAngle);
  }
  
  // Check if we need to move tilt servo
  if (tiltAngle != targetTiltAngle) {
    // Apply smoothing - move a percentage of the remaining distance
    float tiltDiff = targetTiltAngle - tiltAngle;
    int tiltStep = max(1, (int)(tiltDiff * SMOOTH_FACTOR));
    
    // Move toward target position
    if (abs(tiltDiff) <= abs(tiltStep)) {
      tiltAngle = targetTiltAngle;  // We're close enough, go to exact position
    } else if (tiltDiff > 0) {
      tiltAngle += tiltStep;  // Move right
    } else {
      tiltAngle -= tiltStep;  // Move left
    }
    
    // Update servo
    tiltServo.write(tiltAngle);
  }
} 