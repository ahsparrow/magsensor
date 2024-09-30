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
from .mcp2515.canio import Message
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


async def logger(msg_q):
    # Create UART for PICO W comms
    uart = machine.UART(0, 115200)
    writer = asyncio.StreamWriter(uart)

    while True:
        (bell, t) = await msg_q.get()

        writer.write("{},{}\n".format(bell, t))
        await writer.drain()


async def can_receive(can, log_q):
    # Get list of delays(ms) for each bell
    with open("delays.json") as f:
        delays = json.load(f)
        nbells = len(delays)

    # Listen for bell messages
    listener = can.listen()
    while True:
        if listener.in_waiting():
            rx_msg = listener.receive()

            bell = rx_msg.id
            if bell > 0 and bell <= nbells:
                strike_ticks_ms = time.ticks_add(time.ticks_ms(), delays[bell - 1])
                asyncio.create_task(delay(bell, strike_ticks_ms, log_q))

                # Send strike info to logger
                try:
                    log_q.put_nowait((bell, strike_ticks_ms))
                except IndexError:
                    pass

        await asyncio.sleep_ms(0)


async def can_loopback(can):
    while 1:
        for bell in [1, 2, 3, 4, 5, 6, 1, 2, 3, 4, 5, 6]:
            msg = Message(bell, data=b"")

            try:
                can.send(msg)
            except RuntimeError:
                print("Can't send ding message")

            await asyncio.sleep_ms(300)

        await asyncio.sleep_ms(300)


async def main():
    # Create CAN driver
    spi = machine.SPI(0, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
    cs = machine.Pin(9, machine.Pin.OUT, value=1)

    can = MCP2515(spi, cs)
    can.load_filters(MASKS, FILTERS)

    log_q = RingbufQueue(12)

    await asyncio.gather(can_receive(can, log_q), logger(log_q))


async def test():
    # Create CAN driver (in loopback mode)
    spi = machine.SPI(0, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
    cs = machine.Pin(9, machine.Pin.OUT, value=1)

    can = MCP2515(spi, cs, loopback=True, silent=True)
    can.load_filters(MASKS, FILTERS)

    log_q = RingbufQueue(12)

    await asyncio.gather(can_loopback(can), can_receive(can, log_q), logger(log_q))
