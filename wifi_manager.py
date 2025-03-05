import network
import time
import socket
import gc
import config

class WiFiManager:
    def __init__(self):
        self.ssid = config.WIFI_SSID
        self.password = config.WIFI_PASSWORD
        self.wlan = network.WLAN(network.STA_IF)
        self.ip = None
    
    def connect(self):
        """Kết nối đến mạng WiFi"""
        print(f"Đang kết nối đến mạng: {self.ssid}")
        self.wlan.active(True)
        self.wlan.config(pm = 0xa11140)
        if not self.wlan.isconnected():
            self.wlan.connect(self.ssid, self.password)
            # Đợi kết nối hoặc timeout
            max_wait = 20
            while max_wait > 0:
                if self.wlan.isconnected():
                    break
                max_wait -= 1
                print("Đang đợi kết nối...")
                time.sleep(1)
            
        if self.wlan.isconnected():
            self.ip = self.wlan.ifconfig()[0]
            print(f"Đã kết nối thành công! IP: {self.ip}")
            return True
        else:
            print("Kết nối thất bại.")
            return False

    def get_ip(self):
        """Trả về địa chỉ IP của thiết bị"""
        if self.wlan.isconnected():
            return self.wlan.ifconfig()[0]
        return None

