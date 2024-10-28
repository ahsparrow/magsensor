#!/bin/sh

dirs="magsensor magsensor/mcp2515 magsensor/mcp2515/canio magsensor/primitives"

files="
  delays.json
  magsensor/__init__.py
  magsensor/msgid.py
  magsensor/receive.py
  magsensor/mcp2515/__init__.py
  magsensor/mcp2515/spi_device.py
  magsensor/mcp2515/timer.py
  magsensor/mcp2515/canio/__init__.py
  magsensor/primitives/ringbuf_queue.py"

usage() {
  echo "Usage: $0 device"
  exit 1
}

if [ $# -ne 1 ]; then
  usage
fi

# Create new file system (from micropython/ports/rp2/modules/_boot.py)
mpremote connect $1 exec "import rp2; import vfs; vfs.umount('/'); bdev=rp2.Flash(); vfs.VfsLfs2.mkfs(bdev, progsize=256); fs=vfs.VfsLfs2(bdev, progsize=254); vfs.mount(fs, '/')"

# Create directories
for d in $dirs; do
  mpremote connect $1 mkdir :$d
done

# Copy files
for f in $files; do
  mpremote connect $1 cp $f :$f
done

# Copy startup prog
mpremote connect $1 cp main_rx.py :main.py

# Reboot
mpremote connect $1 reset
