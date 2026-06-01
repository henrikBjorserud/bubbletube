#include <Wire.h>
#include <SparkFun_VL53L5CX_Library.h>

#define SDA_PIN 23
#define SCL_PIN 22

#define TOUCH_MM         80
#define SEND_INTERVAL_MS 50

SparkFun_VL53L5CX imager;
VL53L5CX_ResultsData measurementData;

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(1000000);

  if (!imager.begin()) {
    Serial.println("ERROR: VL53L5CX not found, check wiring");
    while (true) delay(1000);
  }

  imager.setResolution(4 * 4);   // 4x4 — faster updates, sufficient for presence detection
  imager.setRangingFrequency(20);
  imager.startRanging();

  Serial.println("READY");
}

#define OUT_OF_RANGE_MM 4000

void loop() {
  if (!imager.isDataReady()) {
    delay(5);
    return;
  }
  if (!imager.getRangingData(&measurementData)) return;

  // Median across all 16 zones; invalid zones count as OUT_OF_RANGE_MM.
  // Median means you must cover >half the sensor view to get a short reading —
  // stepping sideways drops you out immediately rather than lingering.
  uint16_t d[16];
  for (int i = 0; i < 16; i++) {
    uint16_t v = measurementData.distance_mm[i];
    d[i] = (v > 0 && v < OUT_OF_RANGE_MM) ? v : OUT_OF_RANGE_MM;
  }
  // insertion sort
  for (int i = 1; i < 16; i++) {
    uint16_t key = d[i];
    int j = i - 1;
    while (j >= 0 && d[j] > key) { d[j + 1] = d[j]; j--; }
    d[j + 1] = key;
  }
  uint16_t median = (d[7] + d[8]) / 2;

  Serial.print(median);
  Serial.print(",");
  Serial.println(median < TOUCH_MM ? 1 : 0);
}
