DEBUG = True

# Cấu hình WiFi
WIFI_SSID = "test"
WIFI_PASSWORD = "test"

# Cấu hình IRIV Controller
IRIV_IP = "192.168.1.100"  # Thay đổi thành địa chỉ IP thực tế của IRIV Controller
IRIV_PORT = 80

# Cấu hình Modbus/RS485 cho cảm biến QDY30A-B
MODBUS_SLAVE_ADDRESS = 0x01  # Địa chỉ slave mặc định của cảm biến (thường là 1)
# Thanh ghi Modbus RTU cho các tính năng khác nhau
MODBUS_REGISTERS = {
    "WATER_LEVEL": 0x0004,  # Thanh ghi chứa giá trị mực nước
    "TEMPERATURE": 0x0006,  # Thanh ghi chứa giá trị nhiệt độ (nếu có)
    "BATTERY": 0x0008,      # Thanh ghi chứa giá trị pin (nếu có)
    "STATUS": 0x000A        # Thanh ghi chứa trạng thái thiết bị (nếu có)
}

# Cấu hình UART cho RS485
UART_ID = 1
UART_TX_PIN = 8
UART_RX_PIN = 9
UART_DE_PIN = 10  # Có thể là None nếu không sử dụng

# Cấu hình ngưỡng cảnh báo
WATER_THRESHOLD = 2.0  # Ngưỡng mực nước (m)
TEMP1_THRESHOLD = 80.0 # Ngưỡng nhiệt độ cảm biến 1 (°C)
TEMP2_THRESHOLD = 80.0 # Ngưỡng nhiệt độ cảm biến 2 (°C)

# Cấu hình cảnh báo qua email/SMS (nếu có)
EMAIL_SENDER = ""
EMAIL_PASSWORD = ""
EMAIL_RECIPIENT = ""

PHONE_NUMBER = ""

# Thời gian giữa các lần đọc cảm biến (giây)
SENSOR_READ_INTERVAL = 60

# Cấu hình tank
TANK_HEIGHT = 3.0       # Chiều cao bể nước (m)
TANK_CAPACITY = 1000.0  # Dung tích tối đa (lít)

# Hàm tính CRC16 Modbus
def calculate_crc(data):
    """Tính CRC16 Modbus"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF

# Lệnh Modbus RTU mẫu để đọc mực nước từ thanh ghi 0x0004
# Format: [Slave Address, Function Code, Register Hi, Register Lo, Count Hi, Count Lo]
MODBUS_WATER_LEVEL_CMD = bytearray([MODBUS_SLAVE_ADDRESS, 0x03, 0x00, 0x04, 0x00, 0x01])

# Tính và thêm CRC cho lệnh Modbus
crc = calculate_crc(MODBUS_WATER_LEVEL_CMD)
MODBUS_WATER_LEVEL_CMD.append(crc & 0xFF)        # CRC Lo
MODBUS_WATER_LEVEL_CMD.append((crc >> 8) & 0xFF) # CRC Hi

