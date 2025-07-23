from abc import ABC, abstractmethod
from typing import Dict, Any


class Instrument(ABC):
    """Abstract base class for all instruments.

    Parameters
    ----------
    config : dict
        Configuration dictionary for the instrument.

    Attributes
    ----------
    name : str
        Name of the instrument for identification and MQTT topic usage.
    serial_number : str
        Unique identifier for the device.

    Examples
    --------
    >>> inst = SomeInstrument({'name': 'smu1', 'serial_number': 'XYZ'})
    >>> inst.read()
    {'voltage': 1.0, 'current': 0.01}
    """

    def __init__(self, config: Dict[str, Any], resource, logger):
        self.name = config['name']
        self.serial_number = config['serial_number']
        self.config = config
        self.resource = resource
        self.logger = logger


        idn = self.resource.query("*IDN?").strip()
        manufacturer,model,serial,firmware = idn.split(',')

        if self.serial_number != serial:
            raise RuntimeError(f"The serial n umber in the config ({self.serial_number}) does not match the serial number of the instrument ({serial})")

        self.manufacturer = manufacturer
        self.model = model
        self.firmware = firmware

    @abstractmethod
    def reset(self) -> None:
        """Reset the instrument."""
        pass

    @abstractmethod
    def read(self) -> Dict[str, float]:
        """Get current measurement readings (voltage, current, etc.)."""
        pass

    @abstractmethod
    def get_set_values(self) -> Dict[str, float]:
        """Return set values like target voltage and current."""
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any] = None) -> None:
        """Reconfigure the instrument."""
        pass

    @abstractmethod
    def set_output(self, state: bool) -> None:
        """Enable or disable output."""
        pass

    @abstractmethod
    def set_voltage(self, voltage: float) -> None:
        """Set target voltage."""
        pass

    @abstractmethod
    def set_current(self, current: float) -> None:
        """Set target current."""
        pass
