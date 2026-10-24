#!/bin/env python3

"""This script is based on work done in this forum post by "lawrence":
https://forum.buspirate.com/t/sle4442-smart-card-adapter-kf-011c/204/117
"""

import binascii
from time import sleep

# pyserial required.
import serial


#################
# CONFIGURATION #
#################

# SIM settings
SIM_BAUD = 9600
SIM_DATA_BITS = 8
SIM_PARITY = "Even"
SIM_STOP_BITS = 2
SIM_VOLTAGE = 1.8 # Voltage your SIM wants to run at.
SIM_MAX_CURRENT = 50 # Max current draw before cutting the PSU off.

# BusPirate settings
BP_PORT_NAME = '/dev/ttyBPText' # Your BusPirate text console device here.
BP_PORT_BAUD = 115200 # BusPirate serial port speed.
BP_PORT_PARITY = "None"
BP_PORT_STOP_BITS = 1


#####################
# END CONFIGURATION #
#####################

# Map parity setting to PySerial constant.
BP_PORT_PARITY_MAP = {
    "none": serial.PARITY_NONE,
    "even": serial.PARITY_EVEN,
    "odd": serial.PARITY_ODD
}

# Map parity setting to BusPirate menu option.
SIM_PARITY_MAP = {
    "none": 1,
    "even": 2,
    "odd": 3
}

# Map the easy-to-use BusPirate serial parity name to constant.
BP_PORT_PARITY_CONST = BP_PORT_PARITY_MAP[SIM_PARITY.lower()]

# Convert the SIM's baud rate setting to a clock signal in MHz.
SIM_BAUD_TO_CLK_MHZ = (9600 * 372) / 1000000

# Map the easy-to-use parity name to the BusPirate menu choice.
SIM_PARITY_CODE = SIM_PARITY_MAP[SIM_PARITY.lower()]

# Sequence of BusPirate commands to run.
CONFIG_SEQ = [
    # Set HDUART mode, properties
    'm', '4', 'n', str(SIM_BAUD), str(SIM_DATA_BITS), str(SIM_PARITY_CODE), str(SIM_STOP_BITS),

    # Set CLK signal - generate a square at the baud rate's frequency with a 50% duty cycle.
    'G', '1', f"{SIM_BAUD_TO_CLK_MHZ}mhz", '50%', 

    # Pull-up resistors on.
    'P',

    # Activate power supply.
    'W', str(SIM_VOLTAGE), str(SIM_MAX_CURRENT), 

    # Set bridge mode.
    'bridge'
]

# \r \n chracters.
CRLF = [13,10]


def configure_bp(ser):
    """Configure the BusPirate for use with PySim.
    """
    print("Configuring BusPirate...")

    # Set serial RTS for the BusPirate.
    ser.rts = 1

    # Iterate over commands.
    for c in CONFIG_SEQ:
        # Encode command as ASCII string.
        b = c.encode('ascii')
        print("Cmd: ", c)

        # Run command, send "enter" key, flush buffer.
        ser.write(b)
        ser.write(CRLF)
        ser.flush()
        _ = ser.read(1024)

    print("Configuration done.")


def reset_sim(ser):
    """Flash RTS to reset the SIM.
    """

    print("Resetting SIM...")

    ser.rts = 0
    sleep(0.1)
    ser.rts = 1

    print("Reset done.")


def sync_bp(ser):
    """Attempt to get the BusPirate responding to commands.
    """

    print("Syncing BusPirate serial console", end="")

    # Press enter a few times.
    for _ in range(0, 5):
        print(".", end="")

        data = None

        ser.write(CRLF)
        ser.flush()

        # Check for VT100 prompt and answer no.
        try:
            data:str = ser.read(1024).decode("utf8")

            if data.find("VT100 compatible color mode? (Y/n)>"):
                ser.write("n".encode('ascii'))
                ser.write(CRLF)
                ser.flush()

        # Don't care if we didn't get unicode data.
        except UnicodeDecodeError:
            pass

        sleep(0.3)

    print("\n", end="")
    print("Sync done.")


def main():
    """Main entry point for the script.
    """

    # Use our BusPirate's serial port to do a bunch of stuff...
    with serial.Serial(BP_PORT_NAME, BP_PORT_BAUD, parity=BP_PORT_PARITY_CONST, timeout=0.5) as ser:

        # Sync BusPirate console.
        sync_bp(ser)

        # Configure the BusPirate.
        configure_bp(ser)

        # Flush serial port contents.
        data = ser.read(1024)

        # Reset SIM.
        reset_sim(ser)

        # Read and display any output.
        print("Output any post-reset data...")

        for _ in range(5):
            data = ser.read(128)
            print("Output: ", data, "0x" + binascii.hexlify(data).decode('utf8'))

        # Print hints and notes.
        print("Done configuring the BusPirate!")
        print("")
        print("NOTES:")
        print(" - If pySim-shell fails to detect the SIM card wait a few")
        print("   seconds and issue the 'equip' command again.")
        print(" - If using a BusPirate 5 press the button to exit bridge")
        print("   mode to interact with the device again.")
        print("")
        print("You can now run:")
        print(f"pySim-shell.py -d {BP_PORT_NAME} -b {BP_PORT_BAUD}")
        print("")


if __name__ == '__main__':
    main()
