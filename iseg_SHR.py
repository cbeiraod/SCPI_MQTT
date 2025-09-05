from instrument_base import Instrument
from typing import Dict, Any
from threading import Lock

from utilities import find_SCPI

channel_map = {"CH0": "0", "CH1": "1", "CH2": "2", "CH3": "3"}

trip_action_SCPI = {
    "0" : ["no_action"],
    "1" : ["ramp_down"],
    "2" : ["off"],
    "3" : ["off_module"],
    "4" : ["disable_trip"],
}

class ISEGSHR(Instrument):
    """SCPI handler for iSEG SHR quad-channel HV PSU.

    Parameters
    ----------
    config : dict
        Instrument configuration including per-channel voltage/current setpoints.
    resource : pyvisa.resources.Resource
        A VISA instrument resource already matched by serial number.

    Examples
    --------
    >>> config = {
    ...     "name": "psu_1",
    ...     "serial_number": "456789",
    ...     "config": {
    ...         "channels": {
    ...             "CH1": {"voltage": 500.0, "current": 0.0005},
    ...             "CH2": {"voltage": 1200.0, "current": 0.001}
    ...         }
    ...     }
    ... }
    >>> psu = ISEGSHR(config, resource)
    >>> psu.read()
    {'CH1_voltage': 4.98, 'CH1_current': 0.49, 'CH2_voltage': 11.97, 'CH2_current': 0.95, ...}
    """

    # These ISEG devices have a weird feature where they echo the results back which ruins everything and we have to change the approach a bit

    def __init__(self, config: Dict[str, Any], resource, logger):
        super().__init__(config, resource, logger)
        self.mutex_lock = Lock()

        self.channels = config["config"].get("channels", {})
        self.set_values = {ch: vals.copy() for ch, vals in self.channels.items()}

    def reset(self) -> None:
        """Reset the instrument."""
        with self.mutex_lock:
            self.resource.query(":VOLT OFF,(@0-3)")
            self.resource.read()
            self.resource.query("*CLS")
            self.resource.read()
            self.resource.query("*RST")
            self.resource.read()
            self.resource.query(":EVENT CLEAR,(@0-3)")
            self.resource.read()

    def read(self) -> Dict[str, float]:
        """Reads the live output voltage and current of each channel."""
        readings = {}
        with self.mutex_lock:
            for ch in channel_map:
                self.resource.query(f":MEAS:VOLT? (@{channel_map[ch]})")
                voltage = float(self.resource.read().strip()[:-1])
                self.resource.query(f":MEAS:CURR? (@{channel_map[ch]})")
                current = float(self.resource.read().strip()[:-1])
                self.resource.query(f":READ:VOLT:ON? (@{channel_map[ch]})")
                state = int(self.resource.read())
                readings[f"{ch}_voltage"] = voltage
                readings[f"{ch}_current"] = current
                readings[f"{ch}_power_state"] = state
        return readings

    def get_set_values(self) -> Dict[str, float]:
        """Reads the configured (setpoint) voltage and current for each channel."""
        result = {}
        with self.mutex_lock:
            for ch in channel_map:
                self.resource.query(f":READ:VOLT? (@{channel_map[ch]})")
                voltage = float(self.resource.read().strip()[:-1])
                self.resource.query(f":READ:CURR? (@{channel_map[ch]})")
                current = float(self.resource.read().strip()[:-1])
                result[f"{ch}_set_voltage"] = voltage
                result[f"{ch}_set_current"] = current
        return result

    def configure(self, config: Dict[str, Any] = None) -> None:
        if config is None:
            supply_config = self.config['config']
        else:
            supply_config = config['config']


        with self.mutex_lock:
            # Turn off the output and then reset the state
            self.resource.query(":VOLT OFF,(@0-3)")
            self.resource.read()
            self.resource.query("*RST")
            self.resource.read()
            self.resource.query("*CLS")
            self.resource.read()
            self.resource.query(":EVENT CLEAR,(@0-3)")
            self.resource.read()

            # Set Module Ramp % to 25%, emergency ramp to 200% and current ramp to 30%
            self.resource.query(f":CONF:RAMP:VOLT 25")
            self.resource.read()
            self.resource.query(f":CONF:RAMP:VOLT:EMCY 200")
            self.resource.read()
            self.resource.query(f":CONF:RAMP:CURR 30")
            self.resource.read()

            # Retrieve averaging steps
            averaging_steps = supply_config.get("averaging_steps", "64")
            if averaging_steps not in ["1", "16", "64", "256", "512", "1024"]:
                averaging_steps = "64"
            self.resource.query(f":CONF:AVER {averaging_steps}")
            self.resource.read()

            # Retrieve kill enable
            kill_enable = supply_config.get("kill_enable", "0")
            if kill_enable not in ["0", "1"]:
                kill_enable = "0"
            self.resource.query(f":CONF:KILL {kill_enable}")
            self.resource.read()

            # Retrieve fine adjust
            fine_adjust = supply_config.get("fine_adjust", "1")
            if fine_adjust not in ["0", "1"]:
                fine_adjust = "1"
            self.resource.query(f":CONF:ADJUST {fine_adjust}")
            self.resource.read()

            # Loop on channels
            for channel in supply_config.get("channels"):
                channel_config = supply_config["channels"][channel]

                # Retrieve the trip settings
                trip_time_ms = int(float(channel_config.get("trip_time", "0.1"))*1000) # Trip time is defined in seconds
                trip_action = find_SCPI(channel_config, 'trip_action', trip_action_SCPI, '4')
                self.resource.query(f":CONF:TRIP:TIME {trip_time_ms},(@{channel_map[channel]})")
                self.resource.read()
                self.resource.query(f":CONF:TRIP:ACTION {trip_action},(@{channel_map[channel]})")
                self.resource.read()


                # Disable inhibit functionality
                self.resource.query(f":CONF:INH:ACTION 4,(@{channel_map[channel]})")
                self.resource.read()

                # Retrieve output mode (see manual for details, valid modes are 1,2,3 depending on the specific model)
                output_mode = channel_config.get("output_mode", "1") # TODO: Consider making this a text description... but the manual does not specify which number corresponds to which mode...
                if output_mode not in ["1", "2", "3"]:
                    output_mode = "1"
                self.resource.query(f":CONF:OUTPUT:MODE {output_mode},(@{channel_map[channel]})")
                self.resource.read()

                # Retrieve output polarity
                output_polarity = channel_config.get("output_polarity", "n")
                if output_polarity not in ["p", "n"]:
                    output_polarity = "n"
                self.resource.query(f":CONF:OUTPUT:POL {output_polarity},(@{channel_map[channel]})")
                self.resource.read()

                # Retrieve ramp speeds
                ramp_up   = int(channel_config.get("ramp_up", "250"))
                ramp_down = int(channel_config.get("ramp_down", "500"))
                self.resource.query(f":CONF:RAMP:VOLT:UP {ramp_up},(@{channel_map[channel]})")
                self.resource.read()
                self.resource.query(f":CONF:RAMP:VOLT:DOWN {ramp_down},(@{channel_map[channel]})")
                self.resource.read()

                curr_ramp_up   = float(channel_config.get("current_ramp_up", "2E-3"))
                curr_ramp_down = float(channel_config.get("current_ramp_down", "4E-3"))
                self.resource.query(f":CONF:RAMP:CURR:UP {curr_ramp_up},(@{channel_map[channel]})")
                self.resource.read()
                self.resource.query(f":CONF:RAMP:CURR:DOWN {curr_ramp_down},(@{channel_map[channel]})")
                self.resource.read()

                # Retrieve the current range
                current_range = channel_config.get("current_range", "AUTO")
                if current_range.upper() not in ["HIGH", "AUTO"]: # LOW is not yet supported
                    current_range = "AUTO"
                self.resource.query(f":CONF:RANGE:CURR {current_range},(@{channel_map[channel]})")
                self.resource.read()

                # Get default power scheme
                voltage = float(channel_config.get("voltage", 0))
                current = float(channel_config.get("current", 0.0001))
                self.resource.query(f":VOLT {voltage},(@{channel_map[channel]})")
                self.resource.read()
                self.resource.query(f":CURR {current},(@{channel_map[channel]})")
                self.resource.read()

    def set_output(self, state: bool, channel: str = None) -> None:
        """Enable/disable output for one or all channels."""
        if channel is None:
            with self.mutex_lock:
                self.resource.query(f":VOLT {'ON' if state else 'OFF'},(@0-3)")
                self.resource.read()
        else:
            if channel not in channel_map:
                raise ValueError(f"Channel {channel} must be a valid channel.")
            with self.mutex_lock:
                self.resource.query(f":VOLT {'ON' if state else 'OFF'},(@{channel_map[channel]})")
                self.resource.read()

    def set_voltage(self, voltage: float, channel: str = None) -> None:
        """Set voltage setpoint for a channel."""
        if not channel:
            raise ValueError("Channel must be specified for voltage setting.")
        if channel not in channel_map:
            raise ValueError(f"Channel {channel} must be a valid channel.")
        with self.mutex_lock:
            self.resource.query(f":VOLT {voltage},(@{channel_map[channel]})")
            self.resource.read()

    def set_current(self, current: float, channel: str = None) -> None:
        """Set current limit for a channel."""
        if not channel:
            raise ValueError("Channel must be specified for current setting.")
        if channel not in channel_map:
            raise ValueError(f"Channel {channel} must be a valid channel.")
        with self.mutex_lock:
            self.resource.query(f":CURR {current},(@{channel_map[channel]})")
            self.resource.read()
