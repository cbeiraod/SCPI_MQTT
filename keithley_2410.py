from instrument_base import Instrument
from typing import Dict, Any

from utilities import find_SCPI

class Keithley2410(Instrument):
    """Handler for Keithley 2410.

    Examples
    --------
    >>> config = {'name': 'smu1', 'serial_number': 'K1234'}
    >>> smu = Keithley2470(config)
    >>> smu.read()
    {'voltage': 1.2, 'current': 0.05}
    """

    def __init__(self, config: Dict[str, Any], resource):
        super().__init__(config, resource)
        self.configure(config)

    def reset(self) -> None:
        """Reset the instrument."""
        pass

    def read(self) -> Dict[str, float]:
        # Replace with actual SCPI or library call
        return {"voltage": 1.2, "current": 0.05}

    def get_set_values(self) -> Dict[str, float]:
        return {"set_voltage": 1.2, "set_current": 0.1}

    def configure(self, config: Dict[str, Any] = None) -> None:
        # Apply configuration (e.g., range, compliance)
        pass

    def set_output(self, state: bool) -> None:
        # Send command to turn on/off
        pass

    def set_voltage(self, voltage: float) -> None:
        # Command to set voltage
        pass

    def set_current(self, current: float) -> None:
        # Command to set current
        pass
