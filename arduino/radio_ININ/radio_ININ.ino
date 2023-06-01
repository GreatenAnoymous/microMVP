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
#define M2PWM 6
#define M2PH 5
#define M1PWM 4
#define M1PH 3
#define MODE_PIN 7
//#define POWER_PIN 2

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

  Serial.println("--Test monitor--");

  //Set address
  radio.openReadingPipe(pipeNum, addresses[0][0]);

  // Initialize motor driver carrier
  pinMode(MODE_PIN, OUTPUT);
  digitalWrite(MODE_PIN, LOW);

  // Initialize motor driver carrier
  //pinMode(POWER_PIN, OUTPUT);
  //digitalWrite(POWER_PIN, HIGH);

  // Update these if the directions of the wheels are wrong
  digitalWrite(M1PWM, LOW); //0,1 reverse
  digitalWrite(M2PH, LOW);  //1,0 forward

  // Start the radio listening for data
  radio.startListening();
  //runMotors(0, -99);
}

// Vehicle ID
int carID = 8;
int carLevel = (int)(carID-1)/(int)((payloadSize-2)/3);
int carIndex = carID - carLevel*(int)((payloadSize-2)/3);


// Calibration parameters. For all vehicles, at leftMax + rightMax they
// should go roughly along a straight line forward at roughly the same speed
int leftMax = 200;
int rightMax = 200;

// Previous commands
byte hasPreviousCommand = 0;
byte previousLeft = 0;
byte previousRight = 0;

// Run the two motors at different thrusts, negative thrusts makes the wheel
// go backward
void runMotors(int rightThrust, int leftThrust) {
  //Switched order of High/Low for crazyradio
  // Left motor
  
  if (rightThrust >= 0 && leftThrust >= 0) {
    Serial.println("Go straight!");
    digitalWrite(M1PWM, LOW); //0,1 reverse
    digitalWrite(M2PH, LOW);  //1,0 forward
    analogWrite(M1PH, abs(leftThrust)*rightMax / 128);
    analogWrite(M2PWM, abs(rightThrust)*leftMax / 128);
  }
  else if (rightThrust > 0 && leftThrust < 0){
    Serial.println("Turn left!");
    digitalWrite(M1PH, LOW);
    digitalWrite(M2PH, LOW);
    analogWrite(M1PWM, abs(leftThrust)*rightMax / 128);
    analogWrite(M2PWM, abs(rightThrust)*leftMax / 128);
  }
  else if (rightThrust < 0 && leftThrust > 0){
    Serial.println("Turn right!");
    digitalWrite(M1PWM, LOW);
    digitalWrite(M2PWM, LOW);
    analogWrite(M1PH, abs(leftThrust)*rightMax / 128);
    analogWrite(M2PH, abs(rightThrust)*leftMax / 128);
  }
  else{
    Serial.println("Go back!");
    digitalWrite(M2PWM, LOW);
    analogWrite(M2PH, abs(rightThrust)*leftMax / 128);
    digitalWrite(M1PH, LOW);
    analogWrite(M1PWM, abs(leftThrust)*rightMax / 128);
    //digitalWrite(M1PWM, HIGH);
    //digitalWrite(M2PH, HIGH);
  }

}

void processCommand(byte readBuffer[]) {
  Serial.print("car index: ");
  Serial.println(carIndex);
  //Check the correctness of level
  byte lv = readBuffer[(carIndex) * 3 - 2];
  if ((lv & 0x7F) != carLevel)
  {
    Serial.println("Wrong level");
    return;
  }
  
  // Parse the command
  byte lc = readBuffer[carIndex * 3 - 1];
  byte rc = readBuffer[carIndex * 3];

  // Parse and send command to motor
  if (hasPreviousCommand == 0 ||
      (hasPreviousCommand == 1 &&
       (previousLeft != lc || previousRight != rc)
      ))
  {
    Serial.println("Starting sending commands to motors");
    int rightThrust = (rc & 0x7F) * ((rc & 0x80) == 0x80 ? -1 : 1);
    int leftThrust = (lc & 0x7F) * ((lc & 0x80) == 0x80 ? -1 : 1);
    Serial.println(rightThrust + " "+ leftThrust);
    runMotors(rightThrust, leftThrust);

    // Save command
    previousRight = rc;
    previousLeft = lc;
    hasPreviousCommand = 1;
  }
}

int count = 0;
unsigned long startTime = micros();

void loop() {
  byte thrusts[payloadSize];
  // Serial.println("Enter a loop");

  //code to test channel to make sure at least signal is sending
  /*
   if (radio.testCarrier()) {
      Serial.println("test carrier");
      Serial.print("available? ");
      Serial.println(radio.available());
      radio.stopListening();
      radio.startListening();
    }
    */

  if (radio.available()) {
    radio.read(&thrusts, payloadSize * sizeof(byte));

    Serial.println(thrusts[0]);
    Serial.println(thrusts[payloadSize - 1]);
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
        Serial.println();
        Serial.print("Car ID:");
        Serial.println(carID);
        return;
      }
      else {
        Serial.println();
        Serial.println(thrusts[0]);
        Serial.println(thrusts[payloadSize - 1]);
        Serial.println("Bad packet");
        Serial.println();
        //Equivalent of continue
        return;
      }
    }

    //Print out received signal
    Serial.print("Signal ");
    Serial.println(count);
    Serial.print("thrusts: ");

    for (int i = 0; i < payloadSize; i++) {
      Serial.print(thrusts[i]);
      Serial.print(" ");
    }
    
    Serial.println();

    /* Counting how much through put is possible from the radio */
    count = count + 1;
    //    if (count == 100) {
    //      count = 0;
    //      unsigned long endTime = micros();
    //      Serial.println();
    //      Serial.println("--------------------------------");
    //      Serial.print(F("Received 100 signals in "));
    //      Serial.println((endTime - startTime) / 1E6);
    //      Serial.print(100.0 / ((endTime - startTime) / 1E6));
    //      Serial.println(" signals per second");
    //      Serial.println("--------------------------------");
    //      startTime = micros();
    //    }
    
    processCommand(thrusts);

    Serial.println();
  }
}
