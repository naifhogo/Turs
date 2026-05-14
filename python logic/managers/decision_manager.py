import time

class DecisionManager:
    """
    Handles the state machine for solar panel operations:
    1. Sun tracking
    2. Wind-based dust cleaning
    3. Water-based cleaning (fallback)
    4. Idle (emergency or manual override state)
    """

    # Possible states
    STATE_SUN_TRACKING = "SUN_TRACKING"
    STATE_CLEANING_WIND = "CLEANING_WIND"
    STATE_CLEANING_WATER = "CLEANING_WATER"
    STATE_IDLE = "IDLE"

    def __init__(self, sensor_ctrl, actuator_ctrl, cleaning_ctrl, firebase_mgr=None):
        """
        :param sensor_ctrl: Instance of SensorController
        :param actuator_ctrl: Instance of ActuatorController
        :param cleaning_ctrl: Instance of CleaningController
        :param firebase_mgr: (Optional) Instance of FirebaseManager
        """
        self.sensor_ctrl = sensor_ctrl
        self.actuator_ctrl = actuator_ctrl
        self.cleaning_ctrl = cleaning_ctrl
        self.firebase_mgr = firebase_mgr

        # Current system state
        self.system_state = self.STATE_SUN_TRACKING

        # For tracking wind cleaning duration
        self.wind_clean_start_time = None
        self.wind_clean_duration = 15 * 60  # 15 minutes in seconds

        # Thresholds and settings
        self.dust_threshold = 20.0   # e.g., >20% dust triggers cleaning
        self.wind_speed_threshold = 15.0  # e.g., >15 m/s is sufficient for wind cleaning

    def run_logic(self):
        """
        Main method to be called repeatedly (e.g., in a loop from main.py).
        Gathers sensor data, checks system state, performs transitions, and
        updates Firebase (if available).
        """
        # 1. Gather necessary sensor data
        dust_level = self._check_dust_level()      # Indirect dust measurement
        wind_speed = self.sensor_ctrl.get_wind_speed()

        # 2. Check for user overrides (if firebase is integrated)
        if self.firebase_mgr:
            self._handle_overrides()

        # 3. State Machine Logic
        if self.system_state == self.STATE_SUN_TRACKING:
            self._handle_sun_tracking(dust_level, wind_speed)

        elif self.system_state == self.STATE_CLEANING_WIND:
            self._handle_wind_cleaning(dust_level, wind_speed)

        elif self.system_state == self.STATE_CLEANING_WATER:
            self._handle_water_cleaning()

        elif self.system_state == self.STATE_IDLE:
            # Idle means do nothing or minimal actions (e.g., safety override).
            pass

        # 4. (Optional) Log or store updated state in Firebase
        self._update_firebase_state()

    # -----------------------
    # Internal State Handlers
    # -----------------------

    def _handle_sun_tracking(self, dust_level, wind_speed):
        """
        Handles normal operation of tracking the sun, and transitions to
        cleaning states if dust is above threshold.
        """
        # If dust level is high, check wind speed
        if dust_level > self.dust_threshold:
            if wind_speed > self.wind_speed_threshold:
                self._switch_state(self.STATE_CLEANING_WIND)
            else:
                self._switch_state(self.STATE_CLEANING_WATER)
        else:
            # Otherwise, just track the sun
            self.actuator_ctrl.stop_actuators()  # or refine with real sun-tracking logic
            # Example: If you have a method to track sun
            # self._track_sun()

    def _handle_wind_cleaning(self, dust_level, wind_speed):
        """
        If in wind cleaning state, ensure we're tilted toward wind direction
        and wait up to 15 minutes for dust to fall below threshold.
        """
        # If just entered wind cleaning (start_time not set), begin now
        if self.wind_clean_start_time is None:
            self.wind_clean_start_time = time.time()
            self._tilt_for_wind_cleaning()  # calls cleaning_ctrl or actuators

        elapsed = time.time() - self.wind_clean_start_time

        # If dust is now below threshold, go back to sun tracking
        if dust_level <= self.dust_threshold:
            self._switch_state(self.STATE_SUN_TRACKING)
            self.wind_clean_start_time = None
        # If we've exceeded the wind cleaning duration, switch to water cleaning
        elif elapsed > self.wind_clean_duration:
            self._switch_state(self.STATE_CLEANING_WATER)
            self.wind_clean_start_time = None

    def _handle_water_cleaning(self):
        """
        Tries water-based cleaning. If reservoir is empty, logs a warning
        and switches to sun tracking or idle.
        """
        success = self.cleaning_ctrl.clean_with_water()
        if success:
            # After successful water cleaning, revert to sun tracking
            self._switch_state(self.STATE_SUN_TRACKING)
        else:
            # Reservoir is empty or cleaning failed
            self._log_event("WARNING: Water reservoir empty or cleaning failed.")
            # Decide next state (Idle or remain in sun tracking)
            self._switch_state(self.STATE_SUN_TRACKING)

    # -------------------------
    # Supporting / Utility Code
    # -------------------------

    def _switch_state(self, new_state):
        """
        Safely updates the system state. Clears any needed timers or counters.
        """
        self.system_state = new_state
        if new_state != self.STATE_CLEANING_WIND:
            self.wind_clean_start_time = None  # reset wind cleaning timer

    def _handle_overrides(self):
        """
        Checks Firebase for manual user commands (e.g., force cleaning, stop all).
        After processing, clears them as needed.
        """
        override_command = self.firebase_mgr.get_override_command()
        if not override_command:
            return

        if override_command == "force_clean":
            self._switch_state(self.STATE_CLEANING_WATER)
            self._log_event("User override: Forced water cleaning.")
        elif override_command == "stop_all":
            self.actuator_ctrl.stop_actuators()
            self._switch_state(self.STATE_IDLE)
            self._log_event("User override: Stopped all actuators.")
        elif override_command == "resume":
            # Return to normal operation (sun tracking) if it makes sense
            self._switch_state(self.STATE_SUN_TRACKING)
            self._log_event("User override: Resumed sun tracking.")

        # Clear the command in Firebase after handling (optional)
        self.firebase_mgr.clear_override_command()

    def _check_dust_level(self):
        """
        Uses an indirect method (e.g., actual vs. expected power output) to estimate
        dust accumulation. Returns a float percentage (0-100+).
        """
        # If you have a method for that in the sensor controller, delegate to it:
        return self.sensor_ctrl.get_dust_percentage()

    def _tilt_for_wind_cleaning(self):
        """
        Tells the CleaningController or ActuatorController to align the panel
        with the wind direction.
        """
        wind_direction = self.sensor_ctrl.get_wind_direction()  # e.g., 0-359 degrees
        # Example usage:
        self.cleaning_ctrl.tilt_for_wind_cleaning(self.actuator_ctrl, wind_direction)
        # Or directly manipulate the actuator.

    def _update_firebase_state(self):
        """
        If a Firebase manager is present, update the real-time 'systemState' node
        with the current state. Also can push sensor data if needed.
        """
        if self.firebase_mgr:
            self.firebase_mgr.set_system_state({
                "currentState": self.system_state,
                "windCleanStartTime": self.wind_clean_start_time,
            })

    def _log_event(self, message):
        """
        Send a log or warning message to Firebase or a local logger.
        """
        if self.firebase_mgr:
            self.firebase_mgr.log_event({"description": message})
        else:
            print(f"[LOG] {message}")