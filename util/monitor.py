import struct
from machine import SPI, Pin

from magsensor.mcp2515 import MCP2515 as CAN
from magsensor.mcp2515.canio import Message
from magsensor import msgid

# Accept all messages
MASKS = [0x0, 0x0]
FILTERS = [0x0, 0x0, 0x0, 0x0, 0x0, 0x0]


def can_task():
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    cs = Pin(9, Pin.OUT, value=1)

    can = CAN(spi, cs)
    can.load_filters(MASKS, FILTERS)

    listener = can.listen()

    # Broadcast ECHO request
    msg = Message(msgid.ECHO, b"")
    can.send(msg)

    while True:
        if listener.in_waiting():
            rx_msg = listener.receive()

            if rx_msg.id == msgid.ACK:
                print(f"ACK: bell {rx_msg.data[0]}, {bytes(rx_msg.data)}")

            elif rx_msg.id == msgid.SET:
                print(f"SET: bell {rx_msg.data[0]}, {bytes(rx_msg.data)}")

            elif rx_msg.id < 16:
                delay = struct.unpack("<H", rx_msg.data)[0]
                print(f"DING: bell {rx_msg.id}, delay {delay} , {bytes(rx_msg.data)}")


if __name__ == "__main__":
    can_task()
