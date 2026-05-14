import time
import math

class ActuatorController:
    """
    Controls two actuators:
      1) Base Actuator (0-360°): like the "body" rotation.
      2) Tilt Actuator (0-90°): like the "neck" tilt.

    - For normal sun tracking, the top tilt (neck) is the main driver.
    - The base rotates (body) only if the required tilt is out of range
      or if we have a large horizontal change (e.g., wind from an opposite direction).

    Supports both 'simulated' (no actual motor movement)
    and 'real' (GPIO/servo control) modes.
    """

    def __init__(self, mode="simulated"):
        """
        :param mode: 'simulated' or 'real'
        """
        self.mode = mode

        # Track current angles
        self.current_base_angle = 0.0  # in degrees, range [0..360)
        self.current_tilt_angle = 0.0  # in degrees, range [0..90]

        if self.mode == "real":
            self._initialize_hardware()

    # ------------------------------------------------------
    # Public Methods (Existing)
    # ------------------------------------------------------

    def rotate_base_to(self, target_angle):
        """
        Rotates the base (azimuth) actuator to the specified angle [0..360).
        In 'simulated' mode, just updates the variable.
        In 'real' mode, commands the motor to move.
        """
        target_angle = target_angle % 360

        if self.mode == "simulated":
            print(f"[Simulated] Rotating base from {self.current_base_angle}° to {target_angle}°")
            self.current_base_angle = target_angle
        else:
            self._rotate_base_hardware(target_angle)

    def tilt_top_to(self, target_angle):
        """
        Tilts the top actuator (elevation) to the specified angle [0..90].
        In 'simulated' mode, just updates the variable.
        In 'real' mode, commands the motor.
        """
        # Clamp angle to [0..90]
        target_angle = max(0, min(target_angle, 90))

        if self.mode == "simulated":
            print(f"[Simulated] Tilting top from {self.current_tilt_angle}° to {target_angle}°")
            self.current_tilt_angle = target_angle
        else:
            self._tilt_top_hardware(target_angle)

    def stop_actuators(self):
        """
        Immediately stops both actuators. Useful for manual overrides
        or emergency stops.
        """
        if self.mode == "simulated":
            print("[Simulated] Stopping all actuators.")
        else:
            self._stop_hardware()

    # ------------------------------------------------------
    # New Helper Method for Sun Tracking (Neck vs. Body)
    # ------------------------------------------------------

    def move_panel_for_sun(self, desired_azimuth, desired_elevation):
        """
        Moves the panel to align with the given sun azimuth and elevation.
        The top tilt (neck) tries to handle small vertical angles.
        The base (body) only rotates if the desired tilt is out of 0..90 range
        OR if the horizontal difference is too large.

        :param desired_azimuth: 0..360 degrees (where the sun is horizontally)
        :param desired_elevation: the vertical angle of the sun in degrees
                                 (where 0 is horizontal, 90 is straight up).
        """

        # Step 1: Normalize angles
        desired_azimuth %= 360
        # We clamp the elevation to a min of 0 and max of 180 just for logic below
        desired_elevation = max(0, min(desired_elevation, 180))

        # Step 2: Decide if we can achieve the desired elevation with top tilt alone
        # Our top tilt physically only supports 0..90
        if desired_elevation <= 90:
            # We can directly tilt to desired elevation (the "neck" can handle it)
            self.tilt_top_to(desired_elevation)

            # Check how far the sun azimuth is from current_base_angle
            # If it's not drastically different, we can stay put. Otherwise rotate base.
            azimuth_diff = abs(desired_azimuth - self.current_base_angle)
            # For example, if difference > 15 degrees, we rotate the base
            # You can choose a different threshold
            if azimuth_diff > 15:
                self.rotate_base_to(desired_azimuth)

        else:
            # desired_elevation is above 90 (e.g., 100..180).
            # The "neck" can't tilt that far, so let's rotate the base
            # to bring the panel around so the effective tilt is reduced.

            # A simple approach: if sun is "behind" the panel, rotate the base by 180
            # and use a smaller tilt angle from the other side.
            # Example: if desired_elevation is 120, let's effectively do tilt = 60,
            # but also rotate base by 180 to face the opposite direction.

            # We'll rotate base 180 degrees away from desired_azimuth
            opposite_azimuth = (desired_azimuth + 180) % 360

            # Then the new "effective" elevation from the other side is:
            new_elevation = 180 - desired_elevation
            # clamp to [0..90]
            new_elevation = max(0, min(new_elevation, 90))

            # Rotate base to opposite
            self.rotate_base_to(opposite_azimuth)
            # Tilt top to new_elevation
            self.tilt_top_to(new_elevation)

    # ------------------------------------------------------
    # Hardware-Specific (Stub or Real Implementation)
    # ------------------------------------------------------

    def _initialize_hardware(self):
        """Set up GPIO pins, PWM signals, or motor driver connections."""
        pass

    def _rotate_base_hardware(self, target_angle):
        """Command the base actuator from current_base_angle to target_angle."""
        print(f"[Real] (Stub) Rotating base from {self.current_base_angle}° to {target_angle}°")
        self.current_base_angle = target_angle

    def _tilt_top_hardware(self, target_angle):
        """Command the tilt actuator from current_tilt_angle to target_angle."""
        print(f"[Real] (Stub) Tilting top from {self.current_tilt_angle}° to {target_angle}°")
        self.current_tilt_angle = target_angle

    def _stop_hardware(self):
        """Immediately halt any motor movement."""
        print("[Real] (Stub) Stopping hardware actuators.")

    # ------------------------------------------------------
    # Utility Methods (if needed)
    # ------------------------------------------------------

    def _angle_to_duty_cycle(self, angle, servo_type='base'):
        """
        Convert angle to PWM duty cycle for your specific servo range.
        This is just an example and depends on your servo specs.
        """
        if servo_type == 'base':
            angle = angle % 360  # Wrap
            duty_cycle = 2.5 + (angle / 360.0) * 10.0
            return duty_cycle
        elif servo_type == 'tilt':
            # 0..90 => 2.5..7.0 duty cycle (example range)
            duty_cycle = 2.5 + (angle / 90.0) * 4.5
            return duty_cycle
        else:
            return 0.0
