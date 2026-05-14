import time

class CleaningController:
    """
    Manages cleaning operations:
      1. Wind-based cleaning: tilt panels to face wind direction.
      2. Water-based cleaning: activate pump and vibration mechanism.

    Tracks water volume to ensure you don't exceed available supply
    (each cleaning consumes 0.125 L by default).
    """

    def __init__(self, mode="simulated", initial_water_volume=2.0):
        """
        :param mode: 'simulated' or 'real'
        :param initial_water_volume: in liters
        """
        self.mode = mode
        self.water_volume = initial_water_volume
        self.water_usage_per_clean = 0.125  # liters per cleaning operation

        if self.mode == "real":
            self._initialize_hardware()

    # ------------------------------------------------------
    # Public Methods
    # ------------------------------------------------------

    def tilt_for_wind_cleaning(self, actuator_controller, wind_direction):
        """
        Tilts the panel to align with the wind direction, presumably
        to help remove dust via wind force.

        :param actuator_controller: Instance of ActuatorController
        :param wind_direction: angle in degrees (0-359)
        """
        if self.mode == "simulated":
            print(f"[Simulated] Tilting panel toward wind direction: {wind_direction}°")
        else:
            print(f"[Real] Tilting panel for wind cleaning, wind direction: {wind_direction}°")

        # Use the actuator's rotate_base_to, while tilt might remain at a minimal angle
        # or an angle that best exposes the panel to the wind. For simplicity, we'll
        # rotate the base to wind_direction and keep tilt at 0.
        actuator_controller.rotate_base_to(wind_direction)
        actuator_controller.tilt_top_to(0)  # Example: fully flat to catch wind effectively

    def clean_with_water(self):
        """
        Activates water pump and optional vibration mechanism.
        Reduces water volume by water_usage_per_clean.
        Returns True if cleaning is successful, False if there's not enough water.
        """
        if self.water_volume < self.water_usage_per_clean:
            # Not enough water to clean
            print("[CleaningController] Insufficient water for cleaning.")
            return False

        # If sufficient water, proceed with cleaning
        self.water_volume -= self.water_usage_per_clean

        if self.mode == "simulated":
            print(f"[Simulated] Activating water cleaning. Using {self.water_usage_per_clean} L.")
            print(f"[Simulated] Remaining water volume: {self.water_volume:.3f} L")
        else:
            print("[Real] Activating water pump and vibration mechanism.")
            # Trigger hardware
            self._activate_water_pump()
            self._activate_vibration()
            # Example short run
            time.sleep(3)  # Let the water flow for a short period
            self._deactivate_water_pump()
            self._deactivate_vibration()

            print(f"[Real] Water cleaning completed. Remaining volume: {self.water_volume:.3f} L")

        return True

    # ------------------------------------------------------
    # Hardware-Specific (Stub or Real Implementation)
    # ------------------------------------------------------

    def _initialize_hardware(self):
        """
        Setup pump, vibration motor (if any), and any relevant GPIO pins.
        """
        # Example pseudocode:
        # import RPi.GPIO as GPIO
        # GPIO.setmode(GPIO.BCM)
        # GPIO.setup(PUMP_PIN, GPIO.OUT)
        # GPIO.setup(VIBRATION_PIN, GPIO.OUT)
        pass

    def _activate_water_pump(self):
        """
        Turn on the water pump (GPIO HIGH or similar).
        """
        # Example:
        # GPIO.output(PUMP_PIN, GPIO.HIGH)
        print("[Real] (Stub) Water pump ON.")

    def _deactivate_water_pump(self):
        """
        Turn off the water pump (GPIO LOW or similar).
        """
        # Example:
        # GPIO.output(PUMP_PIN, GPIO.LOW)
        print("[Real] (Stub) Water pump OFF.")

    def _activate_vibration(self):
        """
        Turn on any vibration mechanism to loosen dust.
        """
        # Example:
        # GPIO.output(VIBRATION_PIN, GPIO.HIGH)
        print("[Real] (Stub) Vibration ON.")

    def _deactivate_vibration(self):
        """
        Turn off the vibration mechanism.
        """
        # Example:
        # GPIO.output(VIBRATION_PIN, GPIO.LOW)
        print("[Real] (Stub) Vibration OFF.")