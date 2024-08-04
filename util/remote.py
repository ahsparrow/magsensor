import os
import struct


def get_logs():
    logs = os.listdir("/log")
    logs.sort()

    for n, log in enumerate(logs, start=1):
        with open("/log/" + log, "rb") as f:
            # Get four bytes from end of file
            f.seek(-4, 2)
            buf = bytearray(f.read(4))

            # Remove bell number
            buf[3] = 0

            tim = struct.unpack("<I", buf)[0] // 1000
            m, s = divmod(min(tim, 3599), 60)
            print("Touch {: <2} - {: 2}:{:02}".format(n, m, s))


if __name__ == "__main__":
    get_logs()
