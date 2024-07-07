import asyncio
import json
from machine import SPI, Pin
from mcp2515 import MCP2515 as CAN

BELLS = "x1234567890ET"


# Output bell message after a delay
async def delay(bell, delay_ms):
    await asyncio.sleep_ms(delay_ms)
    print(bell, end="")


async def main():
    # Get list of delays(ms) for each bell
    with open("_delays.json") as f:
        delays = json.load(f)
        nbells = len(delays)

    # Create CAN driver
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    cs = Pin(9, Pin.OUT, value=1)

    can = CAN(spi, cs)
    listener = can.listen()

    while True:
        if listener.in_waiting():
            rx_msg = listener.receive()
            bell = rx_msg.id
            if bell > 0 and bell <= nbells:
                asyncio.create_task(delay(BELLS[bell], delays[bell - 1]))

        await asyncio.sleep_ms(0)


if __name__ == "__main__":
    asyncio.run(main())
