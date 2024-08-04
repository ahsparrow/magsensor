import asyncio
import json
import machine
import os
import struct
import time

from .mcp2515 import MCP2515 as CAN
from .primitives import RingbufQueue

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
    spi = machine.SPI(0, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
    cs = machine.Pin(9, machine.Pin.OUT, value=1)

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
    strike_count = 0
    touch_count = 0

    # Maximum one hour's recording, each strike takes 4 bytes
    buf = bytearray(3600 * 4)
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
            if strike_count == 0:
                # Start the touch
                ticks_start = t

            if (strike_count * 4) < len(buf):
                struct.pack_into(
                    "<I",
                    buf,
                    strike_count * 4,
                    (bell << 24) | time.ticks_diff(t, ticks_start),
                )
                strike_count += 1

        elif strike_count > 0:
            # End of touch, if it's the first one delete existing logs
            if touch_count == 0:
                delete_logs()

            with open("/log/log.{:02d}".format(touch_count + 1), "wb") as f:
                f.write(buf[: (strike_count * 4)])

            strike_count = 0
            touch_count += 1


def delete_logs():
    for p in os.listdir("/log"):
        os.remove("/log/" + p)


if __name__ == "__main__":
    asyncio.run(main())
