from instrument_base import Instrument
from typing import Dict, Any


class TTiPL303QMDP(Instrument):
    """Handler for TTi PL303QMD-P power supply with dual channels.

    Parameters
    ----------
    config : dict
        Device configuration and channel setup.

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
    >>> psu = TTiPL303QMD_P(config)
    >>> psu.read()
    {'CH1_voltage': 4.95, 'CH1_current': 0.48, 'CH2_voltage': 11.98, 'CH2_current': 0.97}
    """

    def __init__(self, config: Dict[str, Any], resource):
        super().__init__(config, resource)
        self.channels = config["config"].get("channels", {})
        self.set_values = {ch: vals.copy() for ch, vals in self.channels.items()}
        self.configure(config["config"])

    def reset(self) -> None:
        """Reset the instrument."""
        pass

    def read(self) -> Dict[str, float]:
        # Simulated values, replace with actual instrument reads
        readings = {}
        for ch in self.channels:
            readings[f"{ch}_voltage"] = self.set_values[ch]["voltage"] * 0.99  # Simulate measurement
            readings[f"{ch}_current"] = self.set_values[ch]["current"] * 0.97
        return readings

    def get_set_values(self) -> Dict[str, float]:
        result = {}
        for ch, vals in self.set_values.items():
            result[f"{ch}_set_voltage"] = vals["voltage"]
            result[f"{ch}_set_current"] = vals["current"]
        return result

    def configure(self, config: Dict[str, Any] = None) -> None:
        # Apply channel configurations
        channels = config.get("channels", {})
        for ch, settings in channels.items():
            self.set_voltage(settings["voltage"], channel=ch)
            self.set_current(settings["current"], channel=ch)

    def set_output(self, state: bool, channel: str = None) -> None:
        # Simulate output on/off, for all or specific channel
        if channel:
            print(f"[SIM] Set {channel} output to {'ON' if state else 'OFF'}")
        else:
            for ch in self.channels:
                print(f"[SIM] Set {ch} output to {'ON' if state else 'OFF'}")

    def set_voltage(self, voltage: float, channel: str = None) -> None:
        # Set voltage for a specific channel
        if channel and channel in self.set_values:
            self.set_values[channel]["voltage"] = voltage
        else:
            raise ValueError("Channel must be specified for voltage setting")

    def set_current(self, current: float, channel: str = None) -> None:
        # Set current for a specific channel
        if channel and channel in self.set_values:
            self.set_values[channel]["current"] = current
        else:
            raise ValueError("Channel must be specified for current setting")
