#include <Servo.h>

#define SERVOPINH  6 // horizontal servo
#define SERVOPINV  5 // vertical servo

int tol = 20; // Lowered for sensitivity
int dtime = 50;

Servo horizontal;
int servoh = 90;
int servohLimitHigh = 180;
int servohLimitLow = 0;

Servo vertical;
int servov = 45;
int servovLimitHigh = 150;
int servovLimitLow = 10;

const int ldrlt = A0;
const int ldrrt = A1;
const int ldrld = A2;
const int ldrrd = A3;

const int windPin = A4;

unsigned long lastPrintTime = 0;
const unsigned long printInterval = 1000;

bool paused = false;

void setup() {
  horizontal.attach(SERVOPINH);
  vertical.attach(SERVOPINV);
  horizontal.write(servoh);
  vertical.write(servov);
  delay(100);
  Serial.begin(9600);
}

void loop() {
  // === Wind speed reading ===
  int windValue = analogRead(windPin);
  float voltage = windValue * (5.0 / 1023.0);
  float windSpeed = (voltage / 5.0) * 30.0;

  // === LDR readings ===
  int lt = analogRead(ldrlt);
  int rt = analogRead(ldrrt);
  int ld = analogRead(ldrld);
  int rd = analogRead(ldrrd);

  int avt = (lt + rt) / 2;
  int avd = (ld + rd) / 2;
  int avl = (lt + ld) / 2;
  int avr = (rt + rd) / 2;
  int veg = (avt + avd + avl + avr) / 4;

  // === Wind Protection ===
  if (windSpeed > 5.0) {
    if (!paused) {
      Serial.println("⚠️ High wind detected! Entering SAFE MODE...");
      paused = true;
      servoh = 142;
      servov = 86;
      horizontal.write(servoh);
      vertical.write(servov);
    }

    if (millis() - lastPrintTime >= printInterval) {
      lastPrintTime = millis();
      Serial.println("------ SAFE MODE ------");
      Serial.print("Wind Speed: "); Serial.print(windSpeed); Serial.println(" m/s");
      Serial.print("Horizontal Angle: "); Serial.print(servoh);
      Serial.print(" | Vertical Angle: "); Serial.println(servov);
      Serial.println("------------------------");
    }
    return;
  }

  if (paused && windSpeed <= 5.0) {
    Serial.println("✅ Wind speed normal. Resuming solar tracking.");
    paused = false;
  }

  // === Data print every 1 second ===
  if (millis() - lastPrintTime >= printInterval) {
    lastPrintTime = millis();
    Serial.println("------ TRACKING MODE ------");
    Serial.print("Wind Speed: "); Serial.print(windSpeed); Serial.println(" m/s");
    Serial.print("LDR lt: "); Serial.print(lt);
    Serial.print(" | rt: "); Serial.print(rt);
    Serial.print(" | ld: "); Serial.print(ld);
    Serial.print(" | rd: "); Serial.println(rd);
    Serial.print("veg = "); Serial.println(veg);
    Serial.print("tol = "); Serial.println(tol);
    Serial.print("dtime = "); Serial.println(dtime);
    Serial.print("Horizontal Angle: "); Serial.print(servoh);
    Serial.print(" | Vertical Angle: "); Serial.println(servov);
    Serial.println("----------------------------");
  }

  // === Adjust tol/dtime dynamically ===
  if (veg > 0 && veg < 300) {
    tol = map(veg, 10, 300, 5, 100);
    dtime = map(veg, 10, 300, 100, 50);
  } else {
    tol = 20;
    dtime = 20;
  }

  // === Vertical Tracking ===
  int dvert = avt - avd;
  if (abs(dvert) > tol) {
    int step = max(1, map(abs(dvert), tol, 500, 1, 5));
    if (avt < avd) {
      servov += step;
    } else {
      servov -= step;
    }
    servov = constrain(servov, servovLimitLow, servovLimitHigh);
    vertical.write(servov);
    //Serial.print("⬆️ Vertical move | step: "); Serial.println(step);
    delay(20);
  }

  // === Horizontal Tracking ===
  int dhoriz = avl - avr;
  if (abs(dhoriz) > tol) {
    int step = max(1, map(abs(dhoriz), tol, 500, 1, 5));
    if (avl < avr) {
      servoh -= step;
    } else {
      servoh += step;
    }
    servoh = constrain(servoh, servohLimitLow, servohLimitHigh);
    horizontal.write(servoh);
    //Serial.print("➡️ Horizontal move | step: "); Serial.println(step);
    delay(20);
  }

  delay(dtime);
}