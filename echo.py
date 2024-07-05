import asyncio
from machine import SPI, Pin
from mcp2515 import MCP2515 as CAN
from mcp2515.canio import Message

CAN_ID = 0


async def can_task():
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    cs = Pin(9, Pin.OUT, value=1)

    can = CAN(spi, cs)
    listener = can.listen()

    msg = Message(CAN_ID, b"ECHO")
    can.send(msg)

    while True:
        if listener.in_waiting():
            rx_msg = listener.receive()

            if rx_msg.data == b"ECHO":
                print(f"ECHO received sensor: {rx_msg.id}")

        await asyncio.sleep_ms(0)


async def main():
    try:
        await asyncio.wait_for(can_task(), timeout=1.0)
    except asyncio.TimeoutError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
