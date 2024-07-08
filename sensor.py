import asyncio
from machine import SPI, Pin, unique_id
from mcp2515 import MCP2515 as CAN
from mcp2515.canio import Message
from primitives import RingbufQueue
import struct
import time
import msgid

# Accept messages matching b0000001xxxx (i.e. ignore bell messages and ACKs)
MASKS = [0x7F0, 0x7F0]
FILTERS = [0x10, 0x10, 0x10, 0x10, 0x10, 0x10]

# RP2040 pin assignments
SCK_PIN = 2
MOSI_PIN = 3
MISO_PIN = 4
CAN_CS_PIN = 9
LED_PIN = 18
SENSOR_PIN = 21


async def can_task(msg_q, bell, board_id):
    spi = SPI(0, sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))
    cs = Pin(CAN_CS_PIN, Pin.OUT, value=1)

    can = CAN(spi, cs)
    can.load_filters(MASKS, FILTERS)

    ding_buf = bytearray(board_id)

    listener = can.listen()
    while True:
        # Check for outgoing requests
        if not msg_q.empty():
            # Ding message is two bytes delay + 6 bytes id
            delay = await msg_q.get()
            struct.pack_into("<H", ding_buf, 0, min(delay, 65535))

            msg = Message(id=bell, data=ding_buf)
            can.send(msg)

        # Process incoming messages
        if listener.in_waiting():
            rx_msg = listener.receive()

            # Echo
            if rx_msg.id == msgid.ECHO:
                buf = bytearray(board_id)
                buf[0] = bell
                msg = Message(id=msgid.ACK, data=buf)
                can.send(msg)

            # Bell set
            if (
                rx_msg.id == msgid.SET
                and len(rx_msg.data) == 8
                and rx_msg.data[2:] == board_id[2:]
            ):
                # Set bell number and store it
                bell = rx_msg.data[0]
                with open("_bell.txt", "w") as f:
                    f.write(f"{bell}\n")

                buf = bytearray(board_id)
                buf[0] = bell
                msg = Message(id=msgid.ACK, data=buf)
                can.send(msg)

        await asyncio.sleep_ms(0)


# Send message after specified delay
async def trigger_task(msg_q, delay_ms):
    await asyncio.sleep_ms(delay_ms)
    await msg_q.put(delay_ms)


# Monitor magnetic sensor
async def sensor_task(msg_q):
    pin = Pin(SENSOR_PIN, Pin.IN)
    led = Pin(LED_PIN, Pin.OUT, value=0)

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
    await asyncio.gather(can_task(q, bell, unique_id()), sensor_task(q))


if __name__ == "__main__":
    asyncio.run(main())
