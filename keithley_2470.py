from instrument_base import Instrument
from typing import Dict, Any
from threading import Lock

from utilities import find_SCPI

off_state_SCPI = {
    "NORM" : ["normal", "norm"],
    "ZERO" : ["zero"],
    "HIMP" : ["himpedance", "high impedance", "himp"],
    "GUAR" : ["guard", "guar"],
}

terminals_SCPI = {
    "FRON" : ["fron", "front"],
    "REAR" : ["rear"],
}

remote_SCPI = {
    "ON" : ["on", True],
    "OFF" : ["off", False],
}

voltage_protection_SCPI = ["PROT20", "PROT40", "PROT100", "PROT200", "PROT300", "PROT400", "NONE"]

voltage_ranges = [0.2, 2, 20, 200, 1000] # in V units
current_ranges = [0.01, 0.1, 1, 10, 100, 1000, 10000, 100000, 1000000]  # in uA units


class Keithley2470(Instrument):
    """Handler for Keithley 2470.

    Examples
    --------
    >>> config = {'name': 'smu1', 'serial_number': 'K1234'}
    >>> smu = Keithley2470(config)
    >>> smu.read()
    {'voltage': 1.2, 'current': 0.05}
    """

    def __init__(self, config: Dict[str, Any], resource, logger):
        super().__init__(config, resource, logger)
        self.mutex_lock = Lock()
        self.source_limit = None
        #self.configure(config)

        with self.mutex_lock:
            supply_config = self.config['config']

            # Retrieve source limit
            source_limit = supply_config.get("source_limit", "none")
            if not (isinstance(source_limit, float) or isinstance(source_limit, int)):
                source_limit = None
            else:
                if source_limit < 0:
                    source_limit = -source_limit
            self.source_limit = source_limit


    def reset(self) -> None:
        """Reset the instrument."""
        with self.mutex_lock:
            self.resource.write("*CLS")
            self.resource.write("*RST")

    def read(self) -> Dict[str, float]:
        with self.mutex_lock:
            voltage = float(self.resource.query("MEAS:VOLT?"))
            current = float(self.resource.query("MEAS:CURR?"))
            power = int(self.resource.query("OUTP?"))
        return {"voltage": voltage, "current": current, "power_state": power}

    def get_set_values(self) -> Dict[str, float]:
        with self.mutex_lock:
            voltage = float(self.resource.query("SOUR:VOLT?"))
            current = float(self.resource.query("SOUR:CURR?"))
        return {"set_voltage": voltage, "set_current": current}


    def configure(self, config: Dict[str, Any] = None) -> None:
        if config is None:
            supply_config = self.config['config']
        else:
            supply_config = config['config']

        with self.mutex_lock:
            # Turn off the output and then reset the state
            self.resource.write("OUTP OFF")
            self.resource.write("*RST")
            self.resource.write("SYST:CLE")

            # Retrieve whether to source voltage or current
            source = supply_config.get("source", "voltage").lower()
            if source not in ["voltage", "current"]:
                source = "voltage"

            # Retrieve the Source Range
            source_range_default = 20
            if source == "current":
                source_range_default = 10
            source_range = supply_config.get("source_range", source_range_default)
            if source_range in ["auto", "AUTO"]:
                source_range = "AUTO"
            else:
                if source == "current":
                    if source_range not in current_ranges:
                        source_range = source_range_default
                    source_range = source_range * 1e-6  # Convert uA to amps
                else:
                    if source_range not in voltage_ranges:
                        source_range = source_range_default

            # Retrieve source limit
            source_limit = supply_config.get("source_limit", "none")
            if not (isinstance(source_limit, float) or isinstance(source_limit, int)):
                source_limit = None
            else:
                if source_limit < 0:
                    source_limit = -source_limit
            self.source_limit = source_limit

            # Retrieve the Measurement Ranges
            voltage_measure_range = supply_config.get("voltage_range", 20)
            if voltage_measure_range in ["auto", "AUTO"]:
                voltage_measure_range = "AUTO"

            current_measure_range = supply_config.get("current_range", 10)
            if current_measure_range in ["auto", "AUTO"]:
                current_measure_range = "AUTO"
            current_measure_range = current_measure_range * 1e-6  # Convert uA to amps

            # Set source function first, then set output off state
            # Set Measure function then set source function (since setting measure can change source, according to manual. However their examples do the opposite)
            if source == "voltage":
                self.resource.write("SENS:FUNC \"CURR\"")

                # Set Measurement Range
                if current_measure_range == "AUTO":
                    self.resource.write("SENS:CURR:RANG:AUTO ON")
                else:
                    self.resource.write("SENS:CURR:RANG:AUTO OFF")
                    self.resource.write(f"SENS:CURR:RANG {current_measure_range}")

                self.resource.write("SOUR:FUNC VOLT")

                # Set Source Range
                if source_range == "AUTO":
                    self.resource.write("SOUR:VOLT:RANG:AUTO ON")
                else:
                    self.resource.write("SOUR:VOLT:RANG:AUTO OFF")
                    self.resource.write(f"SOUR:VOLT:RANG {source_range}")

                # Enable read back so we read the actual value and not the set value
                self.resource.write("SOUR:VOLT:READ:BACK ON")

                # Set high capacitance mode (because LGAD) but consider adding an option to control if used in other contexts
                self.resource.write("SOUR:VOLT:HIGH:CAP ON")
            else:
                self.resource.write("SENS:FUNC \"VOLT\"")

                # Set Measurement Range
                if voltage_measure_range == "AUTO":
                    self.resource.write("SENS:VOLT:RANG:AUTO ON")
                else:
                    self.resource.write("SENS:VOLT:RANG:AUTO OFF")
                    self.resource.write(f"SENS:VOLT:RANG {voltage_measure_range}")

                self.resource.write("SOUR:FUNC CURR")

                # Set Source Range
                if source_range == "AUTO":
                    self.resource.write("SOUR:CURR:RANG:AUTO ON")
                else:
                    self.resource.write("SOUR:CURR:RANG:AUTO OFF")
                    self.resource.write(f"SOUR:CURR:RANG {source_range}")

                # Enable read back so we read the actual value and not the set value
                self.resource.write("SOUR:CURR:READ:BACK ON")

                # Set high capacitance mode (because LGAD) but consider adding an option to control if used in other contexts
                self.resource.write("SOUR:CURR:HIGH:CAP ON")

            # Consider implementing source delay
            # SOURC:<func>:DELAY

            # Set Overvoltage Protection if chosen
            overvoltage = supply_config.get("overvoltage_protection", "NONE")
            if overvoltage.upper() not in voltage_protection_SCPI:
                overvoltage = "NONE"
            else:
                overvoltage = overvoltage.upper()
            self.resource.write(f"SOUR:VOLT:PROT {overvoltage}")

            # Off State
            off_state = find_SCPI(supply_config, 'off_state', off_state_SCPI, 'NORM')
            self.resource.write(f"OUTP:SMOD {off_state}")

            # Set Terminals to use front or rear
            terminals = find_SCPI(supply_config, 'terminals', terminals_SCPI, 'FRON')
            self.resource.write(f"ROUT:TERM {terminals}")

            # Set Remote Sense
            remote = find_SCPI(supply_config, 'remote_sense', remote_SCPI, 'OFF')
            self.resource.write(f"SENS:CURR:RSEN {remote}")
            self.resource.write(f"SENS:VOLT:RSEN {remote}")

            # Disable measurement averaging
            self.resource.write("SENS:AVER OFF")

            # Enable Auto Zero
            self.resource.write("SENS:CURR:AZER ON")
            self.resource.write("SENS:VOLT:AZER ON")

            # Set number of PLC Cycles
            nplc = supply_config.get("nplc", 2)
            if not (isinstance(nplc, int) or isinstance(nplc, float)):
                nplc = 1
            else:
                if nplc < 0.01 or nplc > 10:
                    nplc = 1
            self.resource.write(f"SENS:NPLC {nplc}")

            # Set precision
            precision = supply_config.get("precision", 0)
            if not isinstance(precision, int):
                precision = 0
            else:
                if precision < 0 or precision > 16:
                    precision = 0
            self.resource.write(f"FORM:ASC:PREC {precision}")

            # Set limits (current for V source and voltage for I source)
            compliance_voltage = supply_config.get("compliance_voltage", 15)
            if compliance_voltage < -1100 or compliance_voltage > 1100:
                compliance_voltage = 15
            self.resource.write(f"SOUR:CURR:VLIM {compliance_voltage}")

            compliance_current = supply_config.get("compliance_current", 8)
            compliance_current = compliance_current * 1e-6  # Convert uA to amps
            if compliance_current < -1.05 or compliance_current > 1.05:
                compliance_current = 8e-6
            self.resource.write(f"SOUR:VOLT:ILIM {compliance_current}")

    def set_output(self, state: bool) -> None:
        with self.mutex_lock:
            # Send command to turn on/off
            self.resource.write(f"OUTP {'ON' if state else 'OFF'}")

    def set_voltage(self, voltage: float) -> None:
        with self.mutex_lock:
            if self.source_limit is not None:
                if abs(voltage) > self.source_limit:
                    if voltage > 0:
                        voltage = self.source_limit
                    else:
                        voltage = -self.source_limit

            # Command to set voltage
            if "VOLT" in self.resource.query("SOUR:FUNC?"):
                self.resource.write(f"SOUR:VOLT {voltage}")
            else:
                self.logger.warning("Tried to set voltage when in current source")

    def set_current(self, current: float) -> None:
        with self.mutex_lock:
            if self.source_limit is not None:
                if abs(current) > self.source_limit:
                    if current > 0:
                        current = self.source_limit
                    else:
                        current = -self.source_limit

            # Command to set current
            if "CURR" in self.resource.query("SOUR:FUNC?"):
                self.resource.write(f"SOUR:CURR {current}")
            else:
                self.logger.warning("Tried to set current when in voltage source")
