import paho.mqtt.client as mqtt
from typing import Callable, Dict


class MQTTHandler:
    """Manages MQTT connection and publishing/subscribing.

    Parameters
    ----------
    config : dict
        MQTT configuration.

    Examples
    --------
    >>> mqtt_handler = MQTTHandler(mqtt_config)
    >>> mqtt_handler.publish('readings/smu1', '{"voltage": 1.2}')
    """

    def __init__(self, config: Dict):
        self.broker = config['broker']
        self.port = config.get('port', 1883)
        self.readings_topic = config.get('readings_topic', 'readings')
        self.control_topic = config.get('control_topic', 'control')
        self.client = mqtt.Client()

    def __del__(self):
        self.client.loop_stop()
        self.client.disconnect()

    def connect(self, on_message: Callable):
        self.client.on_message = on_message
        self.client.connect(self.broker, self.port)
        self.client.loop_start()

    def subscribe(self, topic: str):
        self.client.subscribe(topic)

    def publish(self, topic: str, payload: str):
        self.client.publish(topic, payload)

