import socket
import json
import time
import config
import machine
import struct

class IRIVController:
    def __init__(self, ip_address=None, port=None, uart_id=None, tx_pin=None, rx_pin=None, de_pin=None):
        # Network connection details
        self.ip_address = ip_address if ip_address else config.IRIV_IP
        self.port = port if port else config.IRIV_PORT
        self.connected = False
        self.last_connect_attempt = 0
        self.reconnect_interval = 30  # Thử kết nối lại sau 30 giây nếu mất kết nối
        
        # UART for RS485 communication with level sensor
        self.uart_id = uart_id if uart_id is not None else config.UART_ID
        self.tx_pin = tx_pin if tx_pin is not None else config.UART_TX_PIN
        self.rx_pin = rx_pin if rx_pin is not None else config.UART_RX_PIN
        self.de_pin = de_pin if de_pin is not None else config.UART_DE_PIN
        
        # Initialize UART for RS485
        self.uart = machine.UART(
            self.uart_id,
            baudrate=9600,
            bits=8,
            parity=None,
            stop=1,
            tx=machine.Pin(self.tx_pin),
            rx=machine.Pin(self.rx_pin)
        )
        
        # Initialize DE/RE pin if provided
        if self.de_pin is not None:
            self.de = machine.Pin(self.de_pin, machine.Pin.OUT)
            self.de.value(0)  # Set to receive mode by default
        
        print(f"IRIVController khởi tạo: UART{self.uart_id}, TX:{self.tx_pin}, RX:{self.rx_pin}, DE/RE:{self.de_pin}")
        print(f"Kết nối IRIV: {self.ip_address}:{self.port}")
        
    def connect(self):
        """Kiểm tra kết nối với IRIV IO Controller"""
        try:
            # Tạo socket TCP và thử kết nối
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # Timeout 3 giây
            sock.connect((self.ip_address, self.port))
            sock.close()
            
            print(f"Đã kết nối thành công với IRIV IO Controller tại {self.ip_address}")
            self.connected = True
            return True
        except Exception as e:
            print(f"Không thể kết nối đến IRIV IO Controller: {e}")
            self.connected = False
            return False
    
    def send_data(self, data):
        """Gửi dữ liệu đến IRIV IO Controller"""
        if not self.connected:
            current_time = time.time()
            if current_time - self.last_connect_attempt > self.reconnect_interval:
                self.connect()
                self.last_connect_attempt = current_time
            
            if not self.connected:
                return False
        
        try:
            # Chuyển dữ liệu thành JSON
            json_data = json.dumps(data)
            
            # Tạo socket và gửi dữ liệu
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.ip_address, self.port))
            
            # Tạo HTTP request
            request = f"POST /api/data HTTP/1.1\r\n"
            request += f"Host: {self.ip_address}\r\n"
            request += "Content-Type: application/json\r\n"
            request += f"Content-Length: {len(json_data)}\r\n"
            request += "Connection: close\r\n\r\n"
            request += json_data
            
            # Gửi request
            sock.sendall(request.encode())
            
            # Nhận phản hồi
            response = sock.recv(1024).decode()
            sock.close()
            
            # Kiểm tra phản hồi
            if "200 OK" in response:
                print("Dữ liệu đã gửi thành công đến IRIV IO Controller")
                return True
            else:
                print(f"Lỗi khi gửi dữ liệu: {response}")
                return False
        except Exception as e:
            print(f"Lỗi khi gửi dữ liệu đến IRIV IO Controller: {e}")
            self.connected = False
            return False
    
    def get_status(self):
        """Lấy trạng thái từ IRIV IO Controller"""
        if not self.connected:
            current_time = time.time()
            if current_time - self.last_connect_attempt > self.reconnect_interval:
                self.connect()
                self.last_connect_attempt = current_time
            
            if not self.connected:
                return None
        
        try:
            # Tạo socket và gửi request
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.ip_address, self.port))
            
            # Tạo HTTP request
            request = f"GET /api/status HTTP/1.1\r\n"
            request += f"Host: {self.ip_address}\r\n"
            request += "Connection: close\r\n\r\n"
            
            # Gửi request
            sock.sendall(request.encode())
            
            # Nhận phản hồi
            response = b""
            while True:
                data = sock.recv(1024)
                if not data:
                    break
                response += data
            
            sock.close()
            
            # Xử lý phản hồi
            response_str = response.decode()
            if "200 OK" in response_str:
                # Tìm phần JSON trong phản hồi
                json_start = response_str.find('{')
                if json_start != -1:
                    json_data = response_str[json_start:]
                    return json.loads(json_data)
                else:
                    print("Không tìm thấy dữ liệu JSON trong phản hồi")
                    return None
            else:
                print(f"Lỗi khi nhận trạng thái: {response_str}")
                return None
        except Exception as e:
            print(f"Lỗi khi nhận trạng thái từ IRIV IO Controller: {e}")
            self.connected = False
            return None

    def calculate_crc(self, data):
        """Tính CRC16 Modbus"""
        return config.calculate_crc(data)

    def read_level_sensor(self):
        """Đọc dữ liệu từ cảm biến mức chất lỏng QDY30A-B qua RS485/Modbus RTU"""
        try:
            # Nếu sử dụng pin DE/RE cho điều khiển hướng RS485
            if self.de_pin is not None:
                self.de.value(1)  # Chế độ gửi dữ liệu
                time.sleep(0.01)  # Delay nhỏ để chuyển chế độ
            
            # Lấy lệnh Modbus từ config
            cmd_data = bytearray(config.MODBUS_WATER_LEVEL_CMD)
            
            # Xóa bộ đệm trước khi gửi
            self.uart.read()
            
            # Gửi lệnh Modbus qua UART
            self.uart.write(cmd_data)
            
            # Chuyển sang chế độ nhận nếu sử dụng DE/RE pin
            if self.de_pin is not None:
                self.de.value(0)  # Chế độ nhận dữ liệu
            
            # Đợi phản hồi (timeout 500ms)
            time.sleep(0.1)
            
            # Đọc phản hồi
            response = self.uart.read()
            
            if not response or len(response) < 5:  # Tối thiểu: addr(1) + func(1) + len(1) + data(1) + CRC(2)
                print(f"Không đủ dữ liệu từ cảm biến: Nhận được {len(response) if response else 0} bytes")
                return None
                
            # Kiểm tra địa chỉ slave và mã hàm
            if response[0] != config.MODBUS_SLAVE_ADDRESS or response[1] != 0x03:
                print(f"Phản hồi không hợp lệ: Slave={response[0]}, Function={response[1]}")
                return None
                
            # Kiểm tra độ dài dữ liệu
            byte_count = response[2]
            if len(response) < byte_count + 5:  # addr + func + len + data + CRC (2)
                print(f"Dữ liệu không đủ: Cần {byte_count + 5} byte, nhận được {len(response)} byte")
                return None
                
            # Kiểm tra CRC
            received_data = response[:-2]
            received_crc = (response[-1] << 8) | response[-2]
            calculated_crc = self.calculate_crc(received_data)
            
            if calculated_crc != received_crc:
                print(f"Lỗi CRC: Nhận được 0x{received_crc:04X}, tính được 0x{calculated_crc:04X}")
                return None
                
            # Đọc giá trị mức nước từ dữ liệu
            if byte_count >= 2:
                # Big Endian (mặc định cho Modbus RTU)
                level_value = (response[3] << 8) | response[4]
                
                # Chuyển sang đơn vị đo thực tế (mm -> m)
                level_meters = level_value / 1000.0
                
                print(f"Mức chất lỏng: {level_value} mm ({level_meters:.3f} m)")
                return level_meters
            else:
                print(f"Không đủ dữ liệu cho giá trị mức nước")
                return None
            
        except Exception as e:
            print(f"Lỗi khi đọc cảm biến mức chất lỏng: {e}")
            return None 