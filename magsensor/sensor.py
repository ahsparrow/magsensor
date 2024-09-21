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
import machine
import struct
import time

from .mcp2515 import MCP2515
from .mcp2515.canio import Message
from .primitives import RingbufQueue
from . import msgid

# Accept messages matching b0001xxxxxxx (i.e. ignore messages from other sensors)
MASKS = [0x780, 0x0]
FILTERS = [0x80, 0x80, 0x0, 0x0, 0x0, 0x0]

# RP2040 pin assignments
SCK_PIN = 2
MOSI_PIN = 3
MISO_PIN = 4
CAN_CS_PIN = 9
LED_PIN = 18
SENSOR_PIN = 21


async def can_task(msg_q, bell, board_id):
    # Ident state
    ident_state = False

    # SPI setup
    spi = machine.SPI(
        0,
        sck=machine.Pin(SCK_PIN),
        mosi=machine.Pin(MOSI_PIN),
        miso=machine.Pin(MISO_PIN),
    )
    cs = machine.Pin(CAN_CS_PIN, machine.Pin.OUT, value=1)

    can = MCP2515(spi, cs, auto_restart=True)
    can.load_filters(MASKS, FILTERS)

    # Message loop
    listener = can.listen()
    while True:
        # Check for outgoing requests
        if not msg_q.empty():
            # Ding message is two bytes delay
            delay = await msg_q.get()
            data = struct.pack("<H", min(delay, 65535))

            if ident_state:
                msg = Message(id=msgid.ACK + bell, data=board_id)
                ident_state = False
            else:
                msg = Message(id=msgid.BELL + bell, data=data)

            try:
                can.send(msg)
            except RuntimeError:
                print("Can't send ding message")

        # Process incoming messages
        if listener.in_waiting():
            rx_msg = listener.receive()

            # Echo
            if rx_msg.id & msgid.CMD_MASK == msgid.ECHO_REQ:
                msg = Message(id=msgid.ACK + bell, data=board_id)
                try:
                    can.send(msg)
                except RuntimeError:
                    print("Can't send echo ACK message")

            # Ident request
            elif rx_msg.id & msgid.CMD_MASK == msgid.IDENT_REQ:
                ident_state = True

            # Bell set
            elif rx_msg.id & msgid.CMD_MASK == msgid.BELL_SET:
                if rx_msg.data == board_id:
                    # Set bell number and store it
                    bell = rx_msg.id & ~msgid.CMD_MASK
                    with open("_bell.txt", "w") as f:
                        f.write(f"{bell}\n")

                    msg = Message(id=msgid.ACK + bell, data=board_id)
                    try:
                        can.send(msg)
                    except RuntimeError:
                        print("Can't send set ACK message")

            else:
                print(f"Unknown message: {rx_msg.id}")

        await asyncio.sleep_ms(0)


# Send message after specified delay
async def trigger_task(msg_q, delay_ms):
    await asyncio.sleep_ms(delay_ms)
    if not msg_q.full():
        await msg_q.put(delay_ms)
    else:
        print("Message queue full")


# Monitor magnetic sensor
async def sensor_task(msg_q):
    pin = machine.Pin(SENSOR_PIN, machine.Pin.IN)
    led = machine.Pin(LED_PIN, machine.Pin.OUT, value=0)

    trigger_delay = 0

    while 1:
        # Wait for sensor active
        while pin.value() == 1:
            await asyncio.sleep_ms(0)

        start = time.ticks_us()
        led.value(1)

        # Start trigger messaging task
        asyncio.create_task(trigger_task(msg_q, trigger_delay))

        # Wait 10ms after sensor last active for "debounce""
        timeout_us = 0
        stop = time.ticks_us()

        while timeout_us < 10000:
            if pin.value() == 0:
                stop = time.ticks_us()
                timeout_us = 0
            else:
                timeout_us = time.ticks_diff(time.ticks_us(), stop)

            await asyncio.sleep_ms(0)

        led.value(0)

        # Calculate delay from sensor start to centre
        trigger_delay = int(time.ticks_diff(stop, start) / 2000)
        trigger_delay = min(trigger_delay, 100)

        await asyncio.sleep_ms(100)


async def main(bell=0):
    # If CAN id not specified read value from file
    if bell == 0:
        try:
            with open("_bell.txt") as f:
                bell = int(f.readline())
                if bell < 1 or bell > 15:
                    bell = 0
                    print("Bell number out of range, using default")

        except (OSError, ValueError):
            print("Can't read bell number, using default")

    q = RingbufQueue(5)
    await asyncio.gather(can_task(q, bell, machine.unique_id()), sensor_task(q))


if __name__ == "__main__":
    asyncio.run(main())
