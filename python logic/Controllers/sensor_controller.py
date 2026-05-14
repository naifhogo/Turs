import random
import time

class SensorController:
    """
    Handles reading from wind, dust (indirectly), and wind direction sensors.
    Can operate in 'simulated' mode or 'real' mode.
    """

    def __init__(self, mode="simulated"):
        """
        :param mode: 'simulated' or 'real'
        """
        self.mode = mode
        # For demonstration, you can tweak these ranges or formulas as needed
        # in simulated mode:
        self._simulated_wind_speed_min = 0.0
        self._simulated_wind_speed_max = 25.0  # m/s
        self._simulated_dust_min = 0.0
        self._simulated_dust_max = 50.0  # up to 50% dust (for simulation)
        self._last_wind_direction = 0    # store the last direction to mimic real sensors in sim

        # If you need initialization for real sensors (GPIO setup, ADC config, etc.):
        if self.mode == "real":
            self._initialize_hardware()

    def get_wind_speed(self):
        """
        Returns the wind speed in m/s.
        If in simulated mode, generate a random value.
        If in real mode, read from actual hardware (placeholder).
        """
        if self.mode == "simulated":
            return random.uniform(self._simulated_wind_speed_min, self._simulated_wind_speed_max)
        else:
            # Replace with real hardware reading
            # Example: read from anemometer sensor connected via GPIO or I2C
            return self._read_wind_speed_hardware()

    def get_dust_percentage(self):
        """
        Returns an estimate of dust accumulation on the panel (0-100+ %).
        In a real system, you'd compare actual vs. expected power output
        or use a dedicated dust sensor. Here we simulate or stub.
        """
        if self.mode == "simulated":
            return random.uniform(self._simulated_dust_min, self._simulated_dust_max)
        else:
            # For real hardware approach, you might do something like:
            #   actual_power = self._read_power_output()
            #   expected_power = self._estimate_expected_power()
            #   dust_percent = (1 - (actual_power / expected_power)) * 100
            #   return max(dust_percent, 0)
            return self._calculate_real_dust_level()

    def get_wind_direction(self):
        """
        Returns the wind direction in degrees (0-359).
        If in simulated mode, generate a random or semi-random value.
        If real, read from a hardware wind vane sensor or an appropriate sensor array.
        """
        if self.mode == "simulated":
            # Option 1: Pure random each time
            # return random.uniform(0, 360)

            # Option 2: Semi-random changes from the last direction
            delta = random.uniform(-30, 30)
            self._last_wind_direction = (self._last_wind_direction + delta) % 360
            return self._last_wind_direction
        else:
            return self._read_wind_direction_hardware()

    # ------------------
    # Hardware Stubs
    # ------------------

    def _initialize_hardware(self):
        """
        If you're in 'real' mode, initialize your hardware resources here.
        For example, configure GPIO pins, initialize I2C, etc.
        """
        # Example:
        # GPIO.setmode(GPIO.BCM)
        # setup pins for the anemometer, direction sensor, power sensor, etc.
        pass

    def _read_wind_speed_hardware(self):
        """
        Actual code to read wind speed from hardware sensors.
        Replace this with your real sensor logic.
        """
        # Example placeholder
        wind_speed = 0.0
        # e.g. read pulses from an anemometer for a certain interval
        # convert pulses to wind speed (m/s) using sensor's datasheet formula
        return wind_speed

    def _calculate_real_dust_level(self):
        """
        Example approach to dust measurement if you have a power sensor:
          dust% = (1 - (actual_power / expected_power)) * 100
        Replace or expand as needed.
        """
        # Example placeholder
        actual_power = self._read_power_output()
        expected_power = self._estimate_expected_power()
        if expected_power == 0:
            return 0.0
        dust_percent = (1 - (actual_power / expected_power)) * 100
        # clamp or adjust as needed
        return max(dust_percent, 0)

    def _read_power_output(self):
        """
        If using a voltage/current sensor, read it here and convert to watts.
        """
        # Placeholder example:
        return 250.0  # some measured value in watts

    def _estimate_expected_power(self):
        """
        Could base on a known solar irradiance level or a reference sensor.
        """
        # Placeholder example
        return 300.0

    def _read_wind_direction_hardware(self):
        """
        Replace with actual code for a wind vane or multi-sensor approach
        to get direction in degrees (0-359).
        """
        # Placeholder example
        return 0.0
