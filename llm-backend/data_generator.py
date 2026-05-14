"""
data_generator.py
-----------------
Simulates real-time solar panel sensor data.
Run this standalone to test data generation, or import into backend_server.py.
"""

import json
import random
import time
import math
from datetime import datetime


class SolarSensorSimulator:
    """
    Generates realistic solar panel sensor readings.
    Simulates a full day cycle so data feels natural over time.
    """

    def __init__(self):
        self.start_time = time.time()
        # Starting dust accumulates slowly over time
        self._dust_base = random.uniform(10, 40)
        self._battery_base = random.uniform(50, 90)

    def _time_of_day_factor(self):
        """Returns 0.0 (night) to 1.0 (noon) based on elapsed time."""
        elapsed = (time.time() - self.start_time) % 86400  # 24h loop
        hour = (elapsed / 3600) % 24
        # Simulate sunlight peaking at hour 12
        factor = max(0, math.sin(math.pi * (hour - 6) / 12))
        return round(factor, 3)

    def generate(self):
        """
        Returns one realistic sensor snapshot as a dict.
        """
        sun_factor = self._time_of_day_factor()

        # Wind speed: realistic gusts with Gaussian noise
        wind_speed = abs(random.gauss(7, 4))
        wind_speed = min(wind_speed, 45.0)

        # Wind direction: 0–359 degrees
        wind_direction = random.randint(0, 359)

        # Dust builds slowly; cleaning events reset it
        self._dust_base += random.uniform(-0.5, 1.2)
        self._dust_base = max(0, min(100, self._dust_base))
        dust_level = round(self._dust_base + random.gauss(0, 2), 1)
        dust_level = max(0, min(100, dust_level))

        # Battery: charges with sun, discharges at night
        charge_rate = sun_factor * 2.0 - 0.5   # positive in day, negative at night
        self._battery_base += charge_rate + random.gauss(0, 0.5)
        self._battery_base = max(5, min(100, self._battery_base))
        battery_pct = round(self._battery_base, 1)

        # Light sensor (lux) follows sun curve
        light_sensor = round(sun_factor * 900 + random.gauss(0, 40), 1)
        light_sensor = max(0, light_sensor)

        # Panel tilt angles
        servo_v = round(random.uniform(20, 80), 1)    # vertical degrees
        servo_h = round(random.uniform(0, 180), 1)    # horizontal degrees

        # Water used in cleaning (liters today)
        water_used_l = round(random.uniform(0, 1.5), 2)

        # Panel temperature (Celsius)
        temperature_c = round(25 + sun_factor * 30 + random.gauss(0, 3), 1)

        return {
            "timestamp": int(time.time() * 1000),
            "wind_speed": round(wind_speed, 2),
            "wind_direction": wind_direction,
            "dust_level": round(dust_level, 1),
            "battery_pct": battery_pct,
            "light_sensor": light_sensor,
            "servo_v": servo_v,
            "servo_h": servo_h,
            "water_used_l": water_used_l,
            "temperature_c": temperature_c,
            "sun_intensity_factor": sun_factor,
        }

    def stream(self, interval_seconds=5):
        """
        Generator: yields a new sensor reading every `interval_seconds`.
        Use in a loop: for reading in simulator.stream(): ...
        """
        while True:
            yield self.generate()
            time.sleep(interval_seconds)


# ── Quick test ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sim = SolarSensorSimulator()
    print("Streaming sensor data every 3 seconds (Ctrl+C to stop)...\n")
    for i, reading in enumerate(sim.stream(interval_seconds=3)):
        print(f"[Reading {i+1}] {datetime.now().strftime('%H:%M:%S')}")
        print(json.dumps(reading, indent=2))
        print()
