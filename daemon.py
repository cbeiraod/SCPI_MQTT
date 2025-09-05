import argparse
import json
import time
import sys
import pyvisa
import threading
import logging
import signal
from typing import Dict, Any
from instrument_base import Instrument
from keithley_2470 import Keithley2470
from keithley_2410 import Keithley2410
from tti_PL303QMDP import TTiPL303QMDP
from mqtt_handler import MQTTHandler
from threading import Lock

INSTRUMENT_CLASSES = {
    "Keithley2470": Keithley2470,
    "Keithley2410": Keithley2410,
    "TTiPL303QMDP": TTiPL303QMDP,
}


time_lock = Lock()
device_specific_skip = ['ASRL/dev/ttyS0::INSTR', 'ASRL/dev/ttyAMA0::INSTR']

def find_matching_resource(resource_manager, instrument: Dict[str, Any]) -> str:

    # If instrument is specified with a specific resource, try to use that
    if 'resource' in instrument:
        try:
            inst = resource_manager.open_resource(instrument['resource'])
            return inst
        except Exception as e:
            raise RuntimeError(f"Instrument with resource '{instrument['resource']}' not found.")

    #  Use serial number matching
    serial_number: str = instrument['serial_number']
    for resource in resource_manager.list_resources():
        if resource in device_specific_skip:
            continue

        try:
            log.debug(f"Processing resource: {resource}")
            inst = resource_manager.open_resource(resource)

            # Configure some options
            inst.timeout = 2000 # Set timeout to 2 seconds
            if 'read_termination' in instrument:
                inst.read_termination = instrument['read_termination']
            if 'write_termination' in instrument:
                inst.write_termination = instrument['write_termination']

            idn = inst.query("*IDN?").strip()
            if idn == '*IDN?':
                idn = inst.read().strip()
            log.debug(f"Got *IDN? response: {idn}")
            manufacturer,model,serial,firmware = idn.split(',')
            if serial_number == serial.strip():
                return inst
        except Exception as e:
            continue
    raise RuntimeError(f"Instrument with serial {serial_number} not found.")


def load_instruments(config_path: str, rm, do_reset: bool, do_config: bool) -> Dict[str, Instrument]:
    with open(config_path) as f:
        data = json.load(f)
    instruments = {}
    for item in data['instruments']:
        cls = INSTRUMENT_CLASSES[item['type']]
        resource = find_matching_resource(rm, item)
        log.debug("Found resource, trying to create class instance")
        inst = cls(item, resource, log)
        log.debug("Created class instance")
        if do_reset:
            inst.reset()
        if do_config:
            inst.configure()
        instruments[item['name']] = inst
    return instruments


def print_readings(instruments: Dict[str, Instrument]):
    for name, inst in instruments.items():
        readings = inst.read()
        set_vals = inst.get_set_values()
        log.info(f"{name}: readings={readings}, set_values={set_vals}")


# For dynamic interval setting
changed_interval = False
change_time = time.time()
next_time = time.time()
interval = 60

def handle_mqtt(msg, instruments):
    """
    Handle incoming MQTT control messages and apply commands to instruments.

    Topic format:
    - Single-channel: control/{instrument_name}/{command}
    - Multi-channel:  control/{instrument_name}/{channel}/{command}

    Parameters
    ----------
    msg : paho.mqtt.client.MQTTMessage
        The MQTT message containing topic and payload.
    instruments : dict
        Dictionary mapping instrument names to instrument instances.
    """
    global interval
    global next_time
    global change_time
    global changed_interval

    try:
        log.debug(f"Got message: {msg}")
        topic_parts = msg.topic.split("/")
        if len(topic_parts) < 3:
            return  # Not a valid topic

        _, name, *rest = topic_parts
        instrument = instruments.get(name)
        if not instrument:
            return  # Unknown instrument

        # Parse optional channel
        if len(rest) == 2:
            channel, command = rest
        else:
            channel = None
            command = rest[0]

        # Parse payload as JSON (should be a number or a dict)
        try:
            value = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            log.warning(f"Invalid payload for topic {msg.topic}: {msg.payload}")
            return

        log.debug(f"Trying to process command: {command}")

        with time_lock:
            interval = 1
            changed_interval = True
            change_time = time.time()
            next_time = time.time()

        # Route command
        if command == "set_voltage":
            if channel:
                instrument.set_voltage(value, channel=channel)
            else:
                instrument.set_voltage(value)
        elif command == "set_current":
            if channel:
                instrument.set_current(value, channel=channel)
            else:
                instrument.set_current(value)
        elif command == "output":
            if channel:
                instrument.set_output(value, channel=channel)
            else:
                instrument.set_output(value)
        elif command == "configure":
            if isinstance(value, int):
                if value != 0:
                    instrument.configure()
            else:
                instrument.configure(value)
        elif command == "reset":
            if value != 0:
                instrument.reset()
        else:
            log.error(f"Unknown command: {command}")

        log.debug(f"Done processing command: {command}")

    except Exception as e:
        log.error(f"Error handling MQTT message: {e}")


# For graceful shutdown handling
stop_event = threading.Event()

def measurement_loop(arguments):
    global interval
    global next_time
    global change_time
    global changed_interval

    args = arguments
    native_interval = args.interval
    interval = native_interval

    rm = pyvisa.ResourceManager()
    instruments = load_instruments(args.config, rm, args.do_reset, args.do_config)

    if args.single_shot:
        print_readings(instruments)
        stop_event.set()
        return 0

    mqtt_handler = None
    if args.mqtt:
        with open(args.mqtt) as f:
            mqtt_config = json.load(f)
        mqtt_handler = MQTTHandler(mqtt_config)
        mqtt_handler.connect(on_message=lambda c, u, msg: handle_mqtt(msg, instruments))
        for name in instruments:
            log.debug(f"Subscribing to: {mqtt_handler.control_topic}/{name}/#")
            mqtt_handler.subscribe(f"{mqtt_handler.control_topic}/{name}/#")

    with time_lock:
        next_time = time.time()

    while not stop_event.is_set():
        for name, inst in instruments.items():
            readings = inst.read()
            set_vals = inst.get_set_values()
            payload = json.dumps({**readings, **set_vals})
            if mqtt_handler:
                mqtt_handler.publish(f"{mqtt_handler.readings_topic}/{name}", payload)
            else:
                log.info(f"{name}: {payload}")

        with time_lock:
            next_time += interval
            if changed_interval and time.time() - change_time > 30:
                changed_interval = False
                interval = native_interval

        while not stop_event.is_set() and time.time() < next_time:
            time.sleep(0.01)



def main():
    parser = argparse.ArgumentParser(description="Instrument Daemon")
    parser.add_argument("--config", required=True, help="Path to instrument JSON")
    parser.add_argument("--mqtt", help="Path to MQTT config JSON")
    parser.add_argument("--interval", type=int, default=10, help="Polling interval (s)")
    parser.add_argument("--single-shot", action="store_true", help="Single shot mode")
    parser.add_argument("--do-reset", action="store_true", help="Reset the instruments on connect")
    parser.add_argument("--do-config", action="store_true", help="Config the instruments on connect")
    parser.add_argument("--debug", action="store_true", help="Enable debugging info")
    args = parser.parse_args()

    # === Logging Setup ===
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    global log
    log = logging.getLogger(__name__)
    if args.debug:
        log.setLevel(logging.DEBUG)

    # === Graceful Shutdown Handling ===
    def _handle_signal(sig, frame):
        log.info("Signal %s received; shutting down…", sig)
        stop_event.set()

    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)


    log.info("Starting the measurement loop")
    thr = threading.Thread(target=measurement_loop, daemon=True, args=(args,))
    thr.start()
    stop_event.wait()

    # clean up
    thr.join(timeout=1)
    log.info("Shutdown complete.")



if __name__ == '__main__':
    sys.exit(main())  # next section explains the use of sys.exit

