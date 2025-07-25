from instrument_base import Instrument
from typing import Dict, Any
from threading import Lock

channel_map = {"CH1": "1", "CH2": "2"}

class TTiPL303QMDP(Instrument):
    """SCPI handler for TTi PL303QMD-P dual-channel PSU.

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
    ...     "serial_number": "TTI-PL303-456789",
    ...     "config": {
    ...         "channels": {
    ...             "CH1": {"voltage": 5.0, "current": 0.5},
    ...             "CH2": {"voltage": 12.0, "current": 1.0}
    ...         }
    ...     }
    ... }
    >>> psu = TTiPL303QMD_P(config, resource)
    >>> psu.read()
    {'CH1_voltage': 4.98, 'CH1_current': 0.49, 'CH2_voltage': 11.97, 'CH2_current': 0.95}
    """

    def __init__(self, config: Dict[str, Any], resource, logger):
        super().__init__(config, resource, logger)
        self.mutex_lock = Lock()

        self.channels = config["config"].get("channels", {})
        self.set_values = {ch: vals.copy() for ch, vals in self.channels.items()}

    def reset(self) -> None:
        """Reset the instrument."""
        with self.mutex_lock:
            self.resource.write("*CLS")
            self.resource.write("*RST")
            self.resource.write("TRIPRST")

    def read(self) -> Dict[str, float]:
        """Reads the live output voltage and current of each channel."""
        readings = {}
        with self.mutex_lock:
            for ch in channel_map:
                voltage = float(self.resource.query(f"V{channel_map[ch]}O?").strip()[:-1])
                current = float(self.resource.query(f"I{channel_map[ch]}O?").strip()[:-2])
                state = int(self.resource.query(f"OP{channel_map[ch]}?"))
                readings[f"{ch}_voltage"] = voltage
                readings[f"{ch}_current"] = current
                readings[f"{ch}_power_state"] = state
        return readings

    def get_set_values(self) -> Dict[str, float]:
        """Reads the configured (setpoint) voltage and current for each channel."""
        result = {}
        with self.mutex_lock:
            for ch in channel_map:
                voltage = float(self.resource.query(f"V{channel_map[ch]}?").strip()[3:])
                current = float(self.resource.query(f"I{channel_map[ch]}?").strip()[3:])
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
            self.resource.write("OPALL 0")
            self.resource.write("*RST")
            self.resource.write("*CLS")
            self.resource.write("TRIPRST")

            # Loop on channels
            for channel in supply_config.get("channels"):
                channel_config = supply_config["channels"][channel]

                # Retrieve the current range
                current_range = channel_config.get("current_range", "HIGH")
                if current_range.upper() not in ["HIGH", "LOW"]:
                    current_range = "HIGH"
                if current_range.upper() == "HIGH":
                    current_range = 2
                else:
                    current_range = 1
                self.resource.write(f"IRANGE{channel_map[channel]} {current_range}")

                if "over_voltage_trip" in channel_config:
                    voltage = float(channel_config.get("over_voltage_trip"))
                    self.resource.write(f"OVP{channel_map[channel]} {voltage}")

                if "over_current_trip" in channel_config:
                    current = float(channel_config.get("over_current_trip"))
                    self.resource.write(f"OCP{channel_map[channel]} {current}")

                damping = float(channel_config.get("damping", "OFF"))
                if damping.upper() not in ["ON", "OFF"]:
                    damping = "OFF"
                if damping.upper() == "ON":
                    damping = 1
                else:
                    damping = 0
                self.resource.write(f"DAMPING{channel_map[channel]} {damping}")

                # Get default power scheme
                voltage = float(channel_config.get("voltage", 0))
                current = float(channel_config.get("current", 0.2))

                self.resource.write(f"V{channel_map[channel]} {voltage}")
                self.resource.write(f"I{channel_map[channel]} {current}")

    def set_output(self, state: bool, channel: str = None) -> None:
        """Enable/disable output for one or all channels."""
        if channel is None:
            with self.mutex_lock:
                self.resource.write(f"OPALL {1 if state else 0}")
        else:
            if channel not in channel_map:
                raise ValueError(f"Channel {channel} must be a valid channel.")
            with self.mutex_lock:
                self.resource.write(f"OP{channel_map[channel]} {1 if state else 0}")

    def set_voltage(self, voltage: float, channel: str = None) -> None:
        """Set voltage setpoint for a channel."""
        if not channel:
            raise ValueError("Channel must be specified for voltage setting.")
        if channel not in channel_map:
            raise ValueError(f"Channel {channel} must be a valid channel.")
        with self.mutex_lock:
            self.resource.write(f"V{channel_map[channel]} {voltage}")

    def set_current(self, current: float, channel: str = None) -> None:
        """Set current limit for a channel."""
        if not channel:
            raise ValueError("Channel must be specified for current setting.")
        if channel not in channel_map:
            raise ValueError(f"Channel {channel} must be a valid channel.")
        with self.mutex_lock:
            self.resource.write(f"I{channel_map[channel]} {current}")
