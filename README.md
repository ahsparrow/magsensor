# Bell Sensor

## Clean install

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

    mpremote edit _delays.json

## Sensor installation

Copy files to the sensor board

    mpremote fs -r cp mcp2515 :
    mpremote fs -r cp primitives :
    mpremote fs cp msgid.py :
    mpremote fs cp sensor.py :
    mpremote fs cp main_tx.py :main.py

## Receiver installation

Edit `_delays.json`, this contains a list of delays (in ms) between
the sensor trigger and strike point for each bell. The number of delays
must be equal to the number of bells. If you are using software delays
in Abel, Virtual Belfry, etc. the delays can all be set to zero.

Copy files to the receiver board

    mpremote fs -f cp mcp2515 :
    mpremote fs cp msgid.py :
    mpremote fs cp receive.py :
    mpremote fs cp main_rx.py :main.py
    mpremote fs cp _delays.json :_delays.json

## Setting the sensor bell id's

For each bell in turn, with the bells down (and stationary) run the
following command from a PC connected to the receiver

    mpremote mount . run setbell.py <bell_num>

where `bell_num` is 1 for the treble, etc., then follow the on-screen
instructions.
