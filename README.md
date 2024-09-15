# Bell Sensor

## Clean Install

Power up the board while holding the BOOTSEL button down. The board will
appear as a USB drive. Copy the
[flash nuke program](https://datasheets.raspberrypi.com/soft/flash_nuke.uf2)
to the board's USB drive, this resets the board's Flash memory.

Now copy the
[Micropython installer](https://micropython.org/download/rp2-pico/rp2-pico-latest.uf2)
to the board's USB drive.

## Connecting to the MicroPython REPL

The board appears as a virtual USB serial port, typically /dev/ttyACM0.

Create a virtualenv and install mpremote

    pip install mpremote

To automatically detect the board and connect to REPL invoke mpremote
with no arguments

    mpremote

To edit a file on the board, for example

    mpremote edit delays.json

## Sensor Installation

Copy files to the sensor board

    mpremote fs cp -r magsensor :
    mpremote fs cp main_tx.py :main.py

## Receiver Installation

Edit `delays.json`, this contains a list of delays (in ms) between
the sensor trigger and strike point for each bell. The number of delays
must be equal to the number of bells. If you are using software delays
in Abel, Virtual Belfry, etc. the receiver delays must all be set to zero.

Copy files to the receiver board

    mpremote fs cp -r magsensor :
    mpremote fs cp -r util :
    mpremote fs cp delays.json :
    mpremote fs cp main_rx.py :main.py
    mpremote fs mkdir :/log

## Setting Sensor Bell Numbers

For each bell in turn and with the bells stationary run the
following command from a PC connected to the receiver

    mpremote mount . exec  "import util.setbell; util.setbell.run(<bell number>)"

where `bell number` is 1 for the treble and so on. Then follow the on-screen
instructions.

## Cabling

The DB9 connector uses the CAN OPEN (not OBD-II) pin out

      2 - CAN_L   Blue/White
      3 - GND     Orange/White
      7 - CAN_H   Blue
      9 - CAN_V+  Orange
