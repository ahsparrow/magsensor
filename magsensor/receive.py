# CANBell - Bell sensor
#
# Copyright (C) 2024  Alan Sparrow
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import json
import time

import machine

from .mcp2515 import MCP2515
from .primitives import RingbufQueue

BELLS = "x1234567890ET"

# Accept all messages
MASKS = [0x0, 0x0]
FILTERS = [0x0, 0x0, 0x0, 0x0, 0x0, 0x0]


# Output the bell message at specified time
async def delay(bell, strike_ticks_ms, log_q):
    t = time.ticks_diff(strike_ticks_ms, time.ticks_ms())
    await asyncio.sleep_ms(t)

    print(BELLS[bell], end="")

    try:
        log_q.put_nowait((bell, strike_ticks_ms))
    except IndexError:
        pass


async def logger(msg_q):
    # Create UART for PICO W comms
    uart = machine.UART(0, 115200)
    writer = asyncio.StreamWriter(uart)

    while 1:
        (bell, t) = await msg_q.get()

        writer.write("{},{}\n".format(bell, t))
        await writer.drain()


async def main():
    # Get list of delays(ms) for each bell
    with open("delays.json") as f:
        delays = json.load(f)
        nbells = len(delays)

    # Create CAN driver
    spi = machine.SPI(0, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
    cs = machine.Pin(9, machine.Pin.OUT, value=1)

    can = MCP2515(spi, cs)
    can.load_filters(MASKS, FILTERS)

    # Create logger
    log_q = RingbufQueue(12)
    asyncio.create_task(logger(log_q))

    # Listen for bell messages
    listener = can.listen()
    while True:
        if listener.in_waiting():
            t = time.ticks_ms()
            rx_msg = listener.receive()

            bell = rx_msg.id
            if bell > 0 and bell <= nbells:
                asyncio.create_task(
                    delay(bell, time.ticks_add(t, delays[bell - 1]), log_q)
                )

        yield


if __name__ == "__main__":
    asyncio.run(main())
