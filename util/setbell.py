from machine import SPI, Pin
import time

from magsensor.mcp2515 import MCP2515
from magsensor.mcp2515.canio import Message
from magsensor import msgid

CHECK_TIMEOUT = 5000
SET_TIMEOUT = 10000

# Accept all messages
MASKS = [0x0, 0x0]
FILTERS = [0x0, 0x0, 0x0, 0x0, 0x0, 0x0]


def setbell(bell):
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    cs = Pin(9, Pin.OUT, value=1)

    can = MCP2515(spi, cs, auto_restart=True)
    can.load_filters(MASKS, FILTERS)

    listener = can.listen()

    print("Checking bells are stationary, please wait...")
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < CHECK_TIMEOUT:
        if listener.in_waiting():
            msg = listener.receive()
            print("ERROR - Detected bell movement.")
            print("Please make sure none of the bells are swinging and try again")
            return

    print("...OK.")

    can.send(Message(id=msgid.IDENT_REQ, data=b""))
    print("Now swing bell", bell)

    start = time.ticks_ms()
    timeout = 0
    while timeout <= SET_TIMEOUT:
        if listener.in_waiting():
            msg = listener.receive()
            if msg.id & msgid.CMD_MASK == msgid.ACK:
                print(
                    f"Bell {msg.id & ~msgid.CMD_MASK} detected, reassigning to {bell}"
                )

                msg.id = msgid.BELL_SET + bell
                can.send(msg)
                return

        timeout = time.ticks_diff(time.ticks_ms(), start)

    if timeout > SET_TIMEOUT:
        print("ERROR - No bell movement detected, please try again")


def run(bell):
    if bell < 1 or bell > 15:
        print("Bell number must be between 1 and 15")
    else:
        setbell(bell)
