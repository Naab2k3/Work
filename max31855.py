import time
from machine import Pin, SPI

class MAX31855:
    def __init__(self, sck, cs, so):
        """
        Khởi tạo cảm biến MAX31855
        
        Tham số:
        - sck: Chân SCK (Serial Clock)
        - cs: Chân CS (Chip Select)  
        - so: Chân SO/DO (Serial/Data Output - MISO)
        """
        self.cs = cs
        self.cs.init(Pin.OUT, value=1)
        
        # Sử dụng giao tiếp SPI tự cài đặt (bit-bang)
        self.sck = sck
        self.sck.init(Pin.OUT, value=0)
        self.so = so
        self.so.init(Pin.IN)
        
    def read_raw(self):
        """Đọc giá trị thô từ MAX31855 (32-bit)"""
        self.cs.value(0)  # Kích hoạt CS (active low)
        time.sleep_us(10)
        
        value = 0
        for i in range(32):
            self.sck.value(1)  # xung clock lên
            time.sleep_us(10)
            value = (value << 1) | self.so.value()  # đọc bit từ SO
            self.sck.value(0)  # xung clock xuống
            time.sleep_us(10)
            
        self.cs.value(1)  # vô hiệu hóa CS
        return value
    
    def read(self):
        """
        Đọc nhiệt độ từ cảm biến MAX31855 (°C)
        Trả về None nếu có lỗi
        """
        raw_value = self.read_raw()
        
        # Kiểm tra các bit cờ lỗi (D16, D2, D1, D0)
        if raw_value & 0x10004:  # Kiểm tra lỗi
            return None
            
        # Nhiệt độ là 14 bit đầu tiên (D31:D18) với bit dấu
        temp_data = (raw_value >> 18) & 0x3FFF
        
        # Nếu bit dấu (D31) = 1, đó là nhiệt độ âm
        if raw_value & 0x80000000:
            # Chuyển 2's complement sang giá trị âm
            temp_data = ~temp_data & 0x1FFF
            temp = -temp_data * 0.25
        else:
            temp = temp_data * 0.25
            
        return temp