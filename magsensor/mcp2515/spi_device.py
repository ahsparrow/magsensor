class SPIDevice():
    def __init__(self, spi_bus, cs_pin):
        self.spi_bus = spi_bus
        self.cs_pin = cs_pin
        self.cs_active_value = False

    def __enter__(self):
        self.cs_pin.value(self.cs_active_value)
        return self.spi_bus

    def __exit__(self, exc_type, exc_value, traceback):
        self.cs_pin.value(not self.cs_active_value)
        return False


