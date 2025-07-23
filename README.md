# SCPI_MQTT


Create venv: python -m venv venv

Install dependencies:
python -m pip install pyvisa
python -m pip install pyvisa-py
python -m pip install psutil
python -m pip install zeroconf
python -m pip install usb
python -m pip install pyusb
python -m pip install paho-mqtt


As su:
echo 'SUBSYSTEM=="usb", MODE="0666", GROUP="usbusers"' >> /etc/udev/rules.d/99-com.rules
(This did not work)





## Service - Currently just ideas
sudo cp labdaemon.service /etc/systemd/system/

Put systemd file in right place, then restart systemd and start daemon:
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable labdaemon.service
sudo systemctl start labdaemon.service


Check status and logs:
sudo systemctl status labdaemon
journalctl -u labdaemon -f

Check publishing
docker exec -it mosquitto mosquitto_sub -v -t 'power/smu_1'

Check DB
docker exec -it influxdb influx

USE power_data
show measurements
show smu_1 - does not seem to work
select * from sensor_data - also does not seem to work
select * from smu_1 - large dump if you have been running for a while
