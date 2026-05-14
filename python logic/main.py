import time

# Import controllers
from Controllers.sensor_controller import SensorController
from Controllers.actuator_controller import ActuatorController
from Controllers.cleaning_controller import CleaningController

# Import managers
from managers.decision_manager import DecisionManager
# from managers.firebase_manager import FirebaseManager  # Uncomment if using Firebase

def main():
    """
    Main entry point for the solar panel system. Instantiates all controllers,
    sets up the DecisionManager, and runs the control loop.
    """

    # 1. Instantiate each controller in either 'simulated' or 'real' mode
    sensor_ctrl = SensorController(mode="simulated")
    actuator_ctrl = ActuatorController(mode="simulated")
    cleaning_ctrl = CleaningController(mode="simulated", initial_water_volume=2.0)

    # 2. (Optional) If you have a Firebase manager, instantiate it here
    # firebase_mgr = FirebaseManager(
    #     firebase_config_path="path/to/credentials.json",
    #     db_url="https://your-firebase-db-url.firebaseio.com/"
    # )
    firebase_mgr = None  # If not using Firebase yet

    # 3. Create the DecisionManager with references to the controllers and Firebase (if any)
    decision_mgr = DecisionManager(
        sensor_ctrl=sensor_ctrl,
        actuator_ctrl=actuator_ctrl,
        cleaning_ctrl=cleaning_ctrl,
        firebase_mgr=firebase_mgr
    )

    # 4. Run your main control loop
    #    - Each iteration calls decision_mgr.run_logic() to handle
    #      sun tracking, cleaning, etc.
    try:
        while True:
            decision_mgr.run_logic()
            time.sleep(2)  # Sleep interval; adjust as needed
    except KeyboardInterrupt:
        print("Shutting down system...")

if __name__ == "__main__":
    main()