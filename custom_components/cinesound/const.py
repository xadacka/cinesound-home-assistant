"""Constants for the Cinesound integration."""

DOMAIN = "cinesound"

# GATT UUIDs (6e403587- prefix family)
SERVICE_UUID = "6e403587-b5a3-f393-e0a9-e50e24dcca9e"
WRITE_UUID = "6e403588-b5a3-f393-e0a9-e50e24dcca9e"
NOTIFY_UUID = "6e403589-b5a3-f393-e0a9-e50e24dcca9e"

# Safety timeout: how long a motor runs before auto-stop (seconds).
# The sofa keeps moving on a single command, so this is the only backstop.
MOTOR_SAFETY_TIMEOUT = 60

CONF_ADDRESS = "address"
CONF_NAME = "name"
