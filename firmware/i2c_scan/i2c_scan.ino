#include <Wire.h>

// Adafruit ESP32 Feather I2C pins
#define SDA_PIN 23
#define SCL_PIN 22

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);
  delay(2000); // let serial monitor connect before first scan
}

void loop() {
  Serial.println("Scanning I2C bus...");

  uint8_t found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    uint8_t err = Wire.endTransmission();
    if (err == 0) {
      Serial.printf("  0x%02X", addr);
      if (addr == 0x52) Serial.print("  <-- VL53L5CX / VL53L7CX");
      if (addr == 0x29) Serial.print("  <-- VL53L0X / VL53L1X");
      if (addr == 0x5A || addr == 0x5B || addr == 0x5C || addr == 0x5D)
        Serial.print("  <-- MPR121 capsense");
      Serial.println();
      found++;
    }
  }

  if (found == 0)
    Serial.println("  No devices found");
  else
    Serial.printf("  %u device(s) found\n", found);

  Serial.println();
  delay(3000);
}
