//This one uses the Arduino Pro Mini
//Change the processor to ATMega328 3.3V, 8 MHz

#include <SPI.h>
#include <RF24.h>
#include "printf.h"

/* Hardware configuration: Set up nRF24L01 radio on SPI bus plus pins 7 & 8 */
RF24 radio(9, 10);
/**********************************************************/

/** For motor carrier **/

//Original
//#define M1PWM 3
//#define M1PH 4
//#define M2PWM 5
//#define M2PH 6
//#define MODE_PIN 7
//#define POWER_PIN 2

//Modified after switch to Crazyradio
#define M2PWM 3
#define M2PH 4
#define M1PWM 5
#define M1PH 6
#define MODE_PIN 7
#define POWER_PIN 2

//Default Crazyradio Address is 0xE7E7E7E7E7
uint64_t addresses[][6] = {0xE7E7E7E7E7};

//Can use any pipe from 1-5
int pipeNum = 1;

//Size in bytes
const int payloadSize = 32;

void setup() {
  Serial.begin(115200);
  printf_begin();

  SPI.begin();

  radio.begin();
  radio.setPALevel(RF24_PA_MAX);
  radio.setChannel(100);
  radio.setDataRate(RF24_2MBPS);
  radio.setPayloadSize(payloadSize);

  //Set address
  radio.openReadingPipe(pipeNum, addresses[0][0]);

  // Initialize motor driver carrier
  pinMode(MODE_PIN, OUTPUT);
  digitalWrite(MODE_PIN, HIGH);

  // Initialize motor driver carrier
  pinMode(POWER_PIN, OUTPUT);
  digitalWrite(POWER_PIN, HIGH);

  // Update these if the directions of the wheels are wrong
  digitalWrite(M1PH, HIGH);
  digitalWrite(M2PH, LOW);

  // Start the radio listening for data
  radio.startListening();
  //runMotors(127, 127);
}

// Vehicle ID
int carID = 1;
int carLevel = (int)(carID-1)/(int)((payloadSize-2)/3);
int carIndex = carID - carLevel*(int)((payloadSize-2)/3);

// Calibration parameters. For all vehicles, at leftMax + rightMax they
// should go roughly along a straight line forward at roughly the same speed
int leftMax = 256;
int rightMax = 256;

// Run the two motors at different thrusts, negative thrusts makes the wheel
// go backward
void runMotors(int rightThrust, int leftThrust) {
  //Switched order of High/Low for crazyradio
  // Left motor
  if (rightThrust > 0) {
    digitalWrite(M1PH, HIGH);
  }
  else {
    digitalWrite(M1PH, LOW);
  }

  // Right motor
  if (leftThrust > 0) {
    digitalWrite(M2PH, LOW);
  }
  else {
    digitalWrite(M2PH, HIGH);
  }

  // Write the motor speeds
  analogWrite(M1PWM, abs(rightThrust)*leftMax / 128);
  analogWrite(M2PWM, abs(leftThrust)*rightMax / 128);
}

void processCommand(byte readBuffer[]) {
  //Check the correctness of level
  byte lv = readBuffer[carIndex * 3 - 2];
  if ((lv & 0x7F) != carLevel)
  {
    return;
  }
  
  // Parse the command
  byte lc = readBuffer[carIndex * 3 - 1];
  byte rc = readBuffer[carIndex * 3];

  // Parse and send command to motor
    int rightThrust = (rc & 0x7F) * ((rc & 0x80) == 0x80 ? -1 : 1);
    int leftThrust = (lc & 0x7F) * ((lc & 0x80) == 0x80 ? -1 : 1);
    runMotors(rightThrust, leftThrust);
  
}

void loop() {
  byte thrusts[payloadSize];

  if (radio.available()) {
    radio.read(&thrusts, payloadSize * sizeof(byte));

    // Bad Packet, will not execute past this if block
    if (thrusts[0] != 'C' || thrusts[payloadSize - 1] != 'M') {
      //Option to print out carID if sent cmd array with all 'Z'
      bool id_get = true;

      //Check if everything is a 'Z'
      for (int x = 0; x < payloadSize; x++) {
        if (thrusts[x] != 'Z')
          id_get = false;
        break;
      }

      if (id_get) {
        return;
      }
      else {
        return;
      }
    }

    processCommand(thrusts);
  }
}
