# SCPI_MQTT


Create venv: python -m venv venv

Install dependencies:
python -m pip install pyvisa
python -m pip install pyvisa-py
python -m pip install psutil
python -m pip install zeroconf
python -m pip install usb
python -m pip install pyusb


As su:
echo 'SUBSYSTEM=="usb", MODE="0666", GROUP="usbusers"' >> /etc/udev/rules.d/99-com.rules
(This did not work)
