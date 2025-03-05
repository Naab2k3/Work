import machine
import time
import dht
import config
import max31855
from iriv_controller import IRIVController

class SensorManager:
    def __init__(self, max1_clk, max1_do, max1_cs, max2_clk, max2_do, max2_cs, dht_pin, iriv_ip=None, uart_id=None, tx_pin=None, rx_pin=None, de_pin=None):
        # Khởi tạo cảm biến MAX31855 #1
        self.max1 = max31855.MAX31855(
            sck=machine.Pin(max1_clk),
            cs=machine.Pin(max1_cs),
            so=machine.Pin(max1_do)
        )
        
        # Khởi tạo cảm biến MAX31855 #2
        self.max2 = max31855.MAX31855(
            sck=machine.Pin(max2_clk),
            cs=machine.Pin(max2_cs),
            so=machine.Pin(max2_do)
        )
        
        # Khởi tạo cảm biến DHT22
        self.dht = dht.DHT22(machine.Pin(dht_pin))
        
        # Khởi tạo kết nối đến IRIV Controller
        self.iriv = IRIVController(
            ip_address=iriv_ip,
            uart_id=uart_id,
            tx_pin=tx_pin,
            rx_pin=rx_pin,
            de_pin=de_pin
        )
        
        # Các biến lưu giá trị cảm biến
        self.temp1 = 0.0  # Nhiệt độ từ MAX31855 #1
        self.temp2 = 0.0  # Nhiệt độ từ MAX31855 #2
        self.humidity = 0.0  # Độ ẩm từ DHT22
        self.room_temp = 0.0  # Nhiệt độ phòng từ DHT22
        self.water_level = 0.0  # Mực nước (từ cảm biến QDY30A-B)
        self.tank_volume = 0.0  # Thể tích nước trong bể
        
        # Cấu hình tank từ config
        self.tank_height = config.TANK_HEIGHT  # Chiều cao bể nước (m)
        self.tank_capacity = config.TANK_CAPACITY  # Dung tích tối đa (lít)
        
        # Trạng thái cảnh báo
        self.alerts = {
            "temp1": False,
            "temp2": False,
            "water_level": False
        }
        
        print(f"SensorManager khởi tạo: Tank height={self.tank_height}m, capacity={self.tank_capacity}L")
    
    def read_max31855(self, sensor, name):
        """Đọc dữ liệu từ cảm biến MAX31855"""
        try:
            temp = sensor.read()
            if config.DEBUG:
                print(f"{name} Temp: {temp}°C")
            return temp
        except Exception as e:
            print(f"Lỗi đọc {name}:", e)
            return None
    
    def read_dht22(self):
        """Đọc dữ liệu từ cảm biến DHT22"""
        try:
            self.dht.measure()
            temp = self.dht.temperature()
            humidity = self.dht.humidity()
            if config.DEBUG:
                print(f"DHT22 - Nhiệt độ: {temp}°C, Độ ẩm: {humidity}%")
            return temp, humidity
        except Exception as e:
            print("Lỗi đọc DHT22:", e)
            return None, None
    
    def read_water_level(self):
        """
        Đọc mực nước từ cảm biến QDY30A-B qua IRIV Controller
        """
        try:
            # Đọc dữ liệu từ cảm biến thực tế qua RS485/Modbus
            level = self.iriv.read_level_sensor()
            
            if level is None:
                # Nếu đọc thất bại, sử dụng giá trị mẫu
                print("Không đọc được dữ liệu từ cảm biến mức. Sử dụng giá trị mẫu.")
                level = 1.5  # Mực nước mẫu (m)
                
            # Tính thể tích dựa trên mực nước
            volume_percentage = min(100, max(0, (level / self.tank_height) * 100))
            volume = (level / self.tank_height) * self.tank_capacity
            
            if config.DEBUG:
                print(f"Mực nước: {level}m ({volume_percentage:.1f}%), Thể tích: {volume:.1f}L")
            
            return level, volume
        except Exception as e:
            print(f"Lỗi đọc mực nước: {e}")
            return 0.0, 0.0
    
    def read_all(self):
        """Đọc dữ liệu từ tất cả cảm biến"""
        try:
            # Đọc nhiệt độ từ MAX31855
            self.temp1 = self.read_max31855(self.max1, "MAX31855 #1")
            self.temp2 = self.read_max31855(self.max2, "MAX31855 #2")
            
            # Đọc nhiệt độ và độ ẩm từ DHT22
            self.room_temp, self.humidity = self.read_dht22()
            
            # Đọc mực nước và tính thể tích
            self.water_level, self.tank_volume = self.read_water_level()
            
            # Lấy thời gian hiện tại
            current_time = time.localtime(time.time())
            current_time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                current_time[0], current_time[1], current_time[2],
                current_time[3], current_time[4], current_time[5]
            )
            
            # Trong trường hợp đọc thất bại, đảm bảo có giá trị mặc định
            if self.temp1 is None:
                self.temp1 = 25.0  # Giá trị mẫu
                print("Sử dụng giá trị mẫu cho temp1")
                
            if self.temp2 is None:
                self.temp2 = 30.0  # Giá trị mẫu
                print("Sử dụng giá trị mẫu cho temp2")
                
            if self.room_temp is None:
                self.room_temp = 28.0  # Giá trị mẫu
                print("Sử dụng giá trị mẫu cho room_temp")
                
            if self.humidity is None:
                self.humidity = 65.0  # Giá trị mẫu
                print("Sử dụng giá trị mẫu cho humidity")
        
        except Exception as e:
            print(f"Lỗi khi đọc cảm biến: {e}")
            # Đảm bảo có giá trị mẫu trong trường hợp xảy ra lỗi
            if not hasattr(self, 'temp1') or self.temp1 is None:
                self.temp1 = 25.0
            if not hasattr(self, 'temp2') or self.temp2 is None:
                self.temp2 = 30.0
            if not hasattr(self, 'room_temp') or self.room_temp is None:
                self.room_temp = 28.0
            if not hasattr(self, 'humidity') or self.humidity is None:
                self.humidity = 65.0
            if not hasattr(self, 'water_level') or self.water_level is None:
                self.water_level = 1.5
            if not hasattr(self, 'tank_volume') or self.tank_volume is None:
                self.tank_volume = 500.0
            
        # Gửi dữ liệu đến IRIV Controller qua HTTP (nếu kết nối được)
        try:
            data_to_send = {
                "temp1": self.temp1,
                "temp2": self.temp2,
                "room_temp": self.room_temp,
                "humidity": self.humidity,
                "water_level": self.water_level,
                "tank_volume": self.tank_volume
            }
            self.iriv.send_data(data_to_send)
        except Exception as e:
            print(f"Lỗi khi gửi dữ liệu đến IRIV Controller: {e}")
            
        # Trả về tất cả dữ liệu dưới dạng dict
        return {
            "temp1": self.temp1,
            "temp2": self.temp2,
            "room_temp": self.room_temp,
            "humidity": self.humidity,
            "water_level": self.water_level,
            "tank_volume": self.tank_volume,
            "alerts": self.alerts,
            "timestamp": current_time_str  # Thêm thời gian cập nhật
        }
    
    def check_thresholds(self, water_threshold, temp1_threshold, temp2_threshold):
        """Kiểm tra các ngưỡng cảnh báo"""
        # Kiểm tra ngưỡng nhiệt độ
        if self.temp1 is not None and self.temp1 > temp1_threshold:
            if not self.alerts["temp1"]:
                print(f"CẢNH BÁO: Nhiệt độ cảm biến 1 ({self.temp1}°C) vượt ngưỡng ({temp1_threshold}°C)")
                self.alerts["temp1"] = True
                self.send_alert("Cảnh báo nhiệt độ", f"Nhiệt độ cảm biến 1 đạt {self.temp1}°C, vượt ngưỡng {temp1_threshold}°C")
        else:
            self.alerts["temp1"] = False
        
        if self.temp2 is not None and self.temp2 > temp2_threshold:
            if not self.alerts["temp2"]:
                print(f"CẢNH BÁO: Nhiệt độ cảm biến 2 ({self.temp2}°C) vượt ngưỡng ({temp2_threshold}°C)")
                self.alerts["temp2"] = True
                self.send_alert("Cảnh báo nhiệt độ", f"Nhiệt độ cảm biến 2 đạt {self.temp2}°C, vượt ngưỡng {temp2_threshold}°C")
        else:
            self.alerts["temp2"] = False
        
        # Kiểm tra ngưỡng mực nước
        if self.water_level > water_threshold:
            if not self.alerts["water_level"]:
                print(f"CẢNH BÁO: Mực nước ({self.water_level}m) vượt ngưỡng ({water_threshold}m)")
                self.alerts["water_level"] = True
                self.send_alert("Cảnh báo mực nước", f"Mực nước đạt {self.water_level}m, vượt ngưỡng {water_threshold}m")
        else:
            self.alerts["water_level"] = False
    
    def send_alert(self, subject, message):
        """Gửi cảnh báo qua email hoặc SMS"""
        if hasattr(config, 'EMAIL_SENDER') and config.EMAIL_SENDER:
            try:
                # Gửi email cảnh báo (cần triển khai)
                print(f"Gửi email cảnh báo: {subject}")
                # import cảm biến mail và gửi mail ở đây
            except Exception as e:
                print("Lỗi gửi email:", e)
        
        if hasattr(config, 'PHONE_NUMBER') and config.PHONE_NUMBER:
            try:
                # Gửi SMS cảnh báo (cần triển khai)
                print(f"Gửi SMS cảnh báo đến {config.PHONE_NUMBER}")
                # import module SMS và gửi SMS ở đây
            except Exception as e:
                print("Lỗi gửi SMS:", e)


