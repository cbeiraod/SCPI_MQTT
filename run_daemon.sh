#!/bin/bash
source /home/cristovao/SCPI/venv/bin/activate
exec python /home/cristovao/SCPI/daemon.py --config /home/cristovao/SCPI/config/instruments.json --mqtt /home/cristovao/SCPI/config/mqtt.json
