import asyncio
import json
from machine import SPI, Pin
from mcp2515 import MCP2515 as CAN
from primitives import RingbufQueue
import os
import struct
import time

BELLS = "x1234567890ET"

# Accept all messages
MASKS = [0x0, 0x0]
FILTERS = [0x0, 0x0, 0x0, 0x0, 0x0, 0x0]


# Output the bell message after a specified delay
async def delay(log_q, delay_ms, bell):
    await asyncio.sleep_ms(delay_ms)

    t = time.ticks_ms()
    print(BELLS[bell], end="")

    try:
        log_q.put_nowait((bell, t))
    except IndexError:
        pass


async def main():
    # Get list of delays(ms) for each bell
    with open("delays.json") as f:
        delays = json.load(f)
        nbells = len(delays)

    # Create CAN driver
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    cs = Pin(9, Pin.OUT, value=1)

    can = CAN(spi, cs)
    can.load_filters(MASKS, FILTERS)

    # Create logger
    log_q = RingbufQueue(12)
    asyncio.create_task(logger(log_q))

    # Listen for bell messages
    listener = can.listen()
    while True:
        if listener.in_waiting():
            rx_msg = listener.receive()
            bell = rx_msg.id
            if bell > 0 and bell <= nbells:
                asyncio.create_task(delay(log_q, delays[bell - 1], bell))

        await asyncio.sleep_ms(0)


async def logger(msg_q):
    count = 0
    buf = bytearray(10000)
    ticks_start = 0

    # Ensure log directory exists
    try:
        os.mkdir("/log")
    except OSError:
        pass

    while 1:
        try:
            (bell, t) = await asyncio.wait_for(msg_q.get(), 5)
        except asyncio.TimeoutError:
            bell = 0

        if bell > 0:
            if count == 0:
                ticks_start = t

            if count < 10000:
                struct.pack_into(
                    "<BL", buf, count * 5, bell, time.ticks_diff(t, ticks_start)
                )
                count += 1

        elif count > 0:
            rotate_logs()
            with open("/log/log.0", "wb") as f:
                f.write(buf[: (count * 5)])

            count = 0


def rotate_logs():
    try:
        os.remove("/log/log.19")
    except OSError:
        pass

    for i in range(19, 0, -1):
        try:
            os.rename("/log/log.{:d}".format(i - 1), "/log/log.{:d}".format(i))
        except OSError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
