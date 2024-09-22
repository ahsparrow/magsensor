import struct
from machine import SPI, Pin

from magsensor.mcp2515 import MCP2515
from magsensor.mcp2515.canio import Message
from magsensor import msgid

# Accept all messages
MASKS = [0x0, 0x0]
FILTERS = [0x0, 0x0, 0x0, 0x0, 0x0, 0x0]


def can_task():
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    cs = Pin(9, Pin.OUT, value=1)

    can = MCP2515(spi, cs)
    can.load_filters(MASKS, FILTERS)

    listener = can.listen(timeout=10)

    # ECHO requests
    for bell in range(1, 16):
        msg = Message(msgid.ECHO_REQ + bell, b"")
        can.send(msg)

        rx_msg = listener.receive()
        if rx_msg:
            if rx_msg.id & msgid.CMD_MASK == msgid.ACK:
                print(f"ACK: bell {rx_msg.id & ~msgid.CMD_MASK}, {bytes(rx_msg.data)}")

    while True:
        rx_msg = listener.receive()
        if rx_msg:
            if rx_msg.id & msgid.CMD_MASK == msgid.ACK:
                print(f"ACK: bell {rx_msg.id & ~msgid.CMD_MASK}, {bytes(rx_msg.data)}")

            elif rx_msg.id < 16:
                delay = struct.unpack("<H", rx_msg.data)[0]
                print(f"DING: bell {rx_msg.id}, delay {delay}")


if __name__ == "__main__":
    can_task()
