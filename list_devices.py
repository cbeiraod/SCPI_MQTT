import pyvisa
import sys

device_specific_skip = ['ASRL/dev/ttyS0::INSTR', 'ASRL/dev/ttyAMA0::INSTR']

def main() -> int:
    rm = pyvisa.ResourceManager()

    resources = rm.list_resources()

    for id in resources:
        if id in device_specific_skip:
            continue

        inst = rm.open_resource(id)

        idn = inst.query("*IDN?")
        manufacturer, model, serial, firmware = idn.split(',')

        print(id)
        print(f"\tManufacturer: {manufacturer}")
        print(f"\tModel: {model}")
        print(f"\tSerial: {serial}")
        print(f"\tFirmware Revision: {firmware}")
        #print(f"{id}: {idn}")


    return 0

if __name__ == '__main__':
    sys.exit(main())  # next section explains the use of sys.exit

