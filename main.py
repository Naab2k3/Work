import time
import config
from sensors import SensorManager
from wifi_manager import WiFiManager
from webserver import WebServer

def main():
    # Khởi tạo các chân GPIO cho cảm biến
    # Chỉnh sửa các chân GPIO theo thiết lập thực tế của bạn
    max1_clk = 2  # SCK pin for MAX31855 #1
    max1_do = 1   # SO pin for MAX31855 #1
    max1_cs = 0   # CS pin for MAX31855 #1
    
    max2_clk = 6  # SCK pin for MAX31855 #2
    max2_do = 5   # SO pin for MAX31855 #2
    max2_cs = 4   # CS pin for MAX31855 #2
    
    dht_pin = 15  # DHT22 pin
    
    # Chân kết nối RS485 cho truyền thông với cảm biến mức QDY30A-B
    uart_id = 1        # UART ID (0 or 1)
    rs485_tx_pin = 8   # TX pin của UART
    rs485_rx_pin = 9   # RX pin của UART
    rs485_de_pin = 10  # DE/RE pin của chuyển đổi RS485 (có thể None nếu không sử dụng)
    
    # Thông tin IRIV controller
    iriv_ip = "192.168.1.100"  # Địa chỉ IP của IRIV Controller (đổi sang IP thực tế)
    
    # Khởi tạo quản lý cảm biến
    sensor_manager = SensorManager(
        max1_clk, max1_do, max1_cs,
        max2_clk, max2_do, max2_cs,
        dht_pin,
        iriv_ip=iriv_ip,
        uart_id=uart_id,
        tx_pin=rs485_tx_pin,
        rx_pin=rs485_rx_pin,
        de_pin=rs485_de_pin
    )
    
    # Khởi tạo quản lý WiFi
    wifi_manager = WiFiManager(config.WIFI_SSID, config.WIFI_PASSWORD)
    
    # Kết nối WiFi
    if not wifi_manager.connect():
        print("Không thể kết nối WiFi. Kiểm tra cấu hình.")
        return
    
    # Khởi tạo web server
    web_server = WebServer(wifi_manager, sensor_manager)
    if not web_server.start():
        print("Không thể khởi động web server.")
        return
    
    print("Hệ thống đã sẵn sàng!")
    print(f"Truy cập web UI tại http://{wifi_manager.get_ip()}/")
    
    # Đặt thời gian đọc cảm biến ngắn hơn để kiểm tra
    config.SENSOR_READ_INTERVAL = 60
    
    try:
        # Hiển thị thời gian bắt đầu hệ thống
        start_time = time.localtime(time.time())
        start_time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            start_time[0], start_time[1], start_time[2],
            start_time[3], start_time[4], start_time[5]
        )
        print(f"[BẮT ĐẦU HỆ THỐNG] Thời gian: {start_time_str}")
        print(f"Chu kỳ cập nhật dữ liệu: {config.SENSOR_READ_INTERVAL} giây")
        print("-" * 50)
        
        # Thực hiện đọc dữ liệu cảm biến ban đầu ngay khi khởi động
        print("Đọc dữ liệu cảm biến ban đầu...")
        sensor_data = sensor_manager.read_all()
        print("Dữ liệu cảm biến ban đầu:")
        print(f"Nhiệt độ 1: {sensor_data['temp1']}°C")
        print(f"Nhiệt độ 2: {sensor_data['temp2']}°C")
        print(f"Nhiệt độ phòng: {sensor_data['room_temp']}°C")
        print(f"Độ ẩm: {sensor_data['humidity']}%")
        print(f"Mực nước: {sensor_data['water_level']}m")
        print(f"Thể tích: {sensor_data['tank_volume']}L")
        print("-" * 50)
        
        sensor_manager.check_thresholds(
            config.WATER_THRESHOLD,
            config.TEMP1_THRESHOLD,
            config.TEMP2_THRESHOLD
        )
        last_sensor_read_time = time.time()
        
        last_socket_attempt_time = 0
        
        while True:
            current_time = time.time()
            
            # Đọc dữ liệu từ cảm biến sau mỗi khoảng thời gian cấu hình
            if current_time - last_sensor_read_time >= config.SENSOR_READ_INTERVAL:
                # Đọc dữ liệu từ cảm biến
                sensor_data = sensor_manager.read_all()
                
                # Kiểm tra ngưỡng cảnh báo
                sensor_manager.check_thresholds(
                    config.WATER_THRESHOLD,
                    config.TEMP1_THRESHOLD,
                    config.TEMP2_THRESHOLD
                )
                
                # Cập nhật thời gian đọc cảm biến
                last_sensor_read_time = current_time
                
                # Hiển thị thời gian cụ thể khi hệ thống cập nhật dữ liệu
                update_time = time.localtime(current_time)
                update_time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                    update_time[0], update_time[1], update_time[2],
                    update_time[3], update_time[4], update_time[5]
                )
                print(f"[CẬP NHẬT DỮ LIỆU] Thời gian: {update_time_str} - Đã cập nhật sau {config.SENSOR_READ_INTERVAL} giây")
                print(f"Nhiệt độ 1: {sensor_data['temp1']}°C, Nhiệt độ 2: {sensor_data['temp2']}°C")
                print(f"Nhiệt độ phòng: {sensor_data['room_temp']}°C, Độ ẩm: {sensor_data['humidity']}%")
                print(f"Mực nước: {sensor_data['water_level']}m, Thể tích: {sensor_data['tank_volume']}L")
                print("-" * 50)
            
            # Chỉ kiểm tra socket mỗi 0.5 giây để giảm tải CPU
            if current_time - last_socket_attempt_time >= 0.5:
                try:
                    # Xử lý yêu cầu web
                    web_server.handle_client()
                except Exception as e:
                    print(f"Lỗi xử lý client: {e}")
                
                last_socket_attempt_time = current_time
            
            # Tạm dừng để tiết kiệm năng lượng
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("Chương trình đã dừng bởi người dùng")
    except Exception as e:
        print(f"Lỗi: {e}")
    finally:
        if web_server.sock:
            web_server.sock.close()
        print("Hệ thống đã dừng.")

if __name__ == "__main__":
    main()

