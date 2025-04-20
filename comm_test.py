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

    listener = can.listen(timeout=1000)

    loop = 0
    while True:
        print(loop)
        loop += 1

        for bell in range(1, 7):
            msg = Message(msgid.ECHO_REQ + bell, b"")
            can.send(msg)

            rx_msg = listener.receive()

            if rx_msg is None or rx_msg.id != msgid.ACK + bell:
                print("Bell", bell)
                print(f"Unexpected message id {rx_msg.id}")


if __name__ == "__main__":
    can_task()
