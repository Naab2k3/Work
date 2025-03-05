import socket
import time
import json
import config

class WebServer:
    def __init__(self, wifi_manager, sensor_manager, port=80):
        self.wifi_manager = wifi_manager
        self.sensor_manager = sensor_manager
        self.port = port
        self.sock = None
        
    def start(self):
        """Khởi động web server"""
        if not self.wifi_manager.wlan.isconnected():
            print("Không có kết nối WiFi. Không thể khởi động server.")
            return False
            
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        ip = self.wifi_manager.get_ip()
        addr = ('0.0.0.0', self.port)  # Binding với '0.0.0.0' để chấp nhận kết nối từ tất cả địa chỉ IP
        
        try:
            self.sock.bind(addr)
            self.sock.listen(5)
            print(f"Web server đang chạy tại http://{ip}:{self.port}/")
            print(f"Có thể truy cập từ bất kỳ thiết bị nào trong cùng mạng LAN")
            return True
        except Exception as e:
            print(f"Lỗi khởi động web server: {e}")
            return False
    
    def handle_client(self):
        """Xử lý yêu cầu từ client"""
        # Không bắt ngoại lệ ở đây để ngoại lệ được truyền lên main
        client, addr = self.sock.accept()
        print(f"Kết nối từ {addr}")
        
        # Nhận yêu cầu
        request = client.recv(1024).decode()
        if not request:
            client.close()
            return
        
        # Phân tích yêu cầu
        path = request.split()[1]
        
        # Xử lý các đường dẫn
        if path == "/":
            self.serve_html_page(client)
        elif path == "/data":
            self.serve_sensor_data(client)
        else:
            self.serve_404(client)
            
        client.close()
    
    def serve_html_page(self, client):
        """Phục vụ trang HTML chính với dữ liệu cảm biến được nhúng sẵn"""
        # Lấy dữ liệu cảm biến
        data = self.sensor_manager.read_all()
        
        # Lấy template HTML cơ bản
        html_template = self.get_html_template()
        
        # Thay thế các phần "Đang tải..." bằng dữ liệu thực tế
        html = html_template.replace('<p id="temp1">Đang tải...</p>', 
                                    f'<p id="temp1">{data["temp1"]:.1f}°C</p>')
        html = html.replace('<p id="temp2">Đang tải...</p>', 
                                    f'<p id="temp2">{data["temp2"]:.1f}°C</p>')
        html = html.replace('<p id="room-temp">Đang tải...</p>', 
                                    f'<p id="room-temp">{data["room_temp"]:.1f}°C</p>')
        html = html.replace('<p id="humidity">Đang tải...</p>', 
                                    f'<p id="humidity">{data["humidity"]:.1f}%</p>')
        html = html.replace('<p id="water-level">Đang tải...</p>', 
                                    f'<p id="water-level">{data["water_level"]:.2f}m</p>')
        html = html.replace('<p id="tank-volume">Đang tải...</p>', 
                                    f'<p id="tank-volume">{data["tank_volume"]:.1f}L</p>')
        html = html.replace('<p id="last-update">Đang tải...</p>', 
                                    f'<p id="last-update">{data["timestamp"]}</p>')
        
        # Thêm dữ liệu cảm biến dưới dạng biến JavaScript để trang vẫn có thể sử dụng
        sensor_data_js = f"""
        <script>
        // Dữ liệu cảm biến ban đầu từ server
        const initialSensorData = {json.dumps(data)};
        </script>
        """
        
        # Chèn vào trước thẻ script cuối cùng
        html = html.replace('</body>', f'{sensor_data_js}</body>')
        
        # Gửi phản hồi HTTP
        response = "HTTP/1.1 200 OK\r\n"
        response += "Content-Type: text/html\r\n"
        response += f"Content-Length: {len(html)}\r\n"
        response += "Connection: close\r\n\r\n"
        response += html
        
        client.send(response.encode())
    
    def serve_sensor_data(self, client):
        """Phục vụ dữ liệu cảm biến dưới dạng JSON"""
        # Đọc dữ liệu mới mỗi khi có yêu cầu
        data = self.sensor_manager.read_all()
        
        # Thêm thời gian yêu cầu
        current_time = time.localtime(time.time())
        current_time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            current_time[0], current_time[1], current_time[2],
            current_time[3], current_time[4], current_time[5]
        )
        print(f"[YÊU CẦU DỮ LIỆU WEB] Thời gian: {current_time_str}")
        
        # In thông tin debug
        print("Debug - Dữ liệu cảm biến:")
        print(f"Nhiệt độ 1: {data['temp1']}°C")
        print(f"Nhiệt độ 2: {data['temp2']}°C")
        print(f"Nhiệt độ phòng: {data['room_temp']}°C")
        print(f"Độ ẩm: {data['humidity']}%")
        print(f"Mực nước: {data['water_level']}m")
        print(f"Thể tích: {data['tank_volume']}L")
        print("-" * 50)
        
        try:
            # Đảm bảo tất cả các giá trị đều có thể chuyển đổi thành JSON
            for key in data:
                if key != 'alerts' and data[key] is None:
                    data[key] = 0.0
            
            # Đảm bảo trường alerts luôn tồn tại
            if 'alerts' not in data:
                data['alerts'] = {"temp1": False, "temp2": False, "water_level": False}
            
            # Chuyển đổi dữ liệu sang JSON
            json_data = json.dumps(data)
            
            # Chuyển đổi JSON thành bytes trước khi tính toán độ dài
            json_bytes = json_data.encode()
            
            # Tạo response hoàn chỉnh
            response = "HTTP/1.1 200 OK\r\n"
            response += "Content-Type: application/json\r\n"
            response += f"Content-Length: {len(json_bytes)}\r\n"
            response += "Connection: close\r\n\r\n"
            
            # Kết hợp headers và nội dung thành một message duy nhất
            complete_response = response.encode() + json_bytes
            
            # Gửi toàn bộ response trong một lần
            client.sendall(complete_response)
        
        except Exception as e:
            print(f"Lỗi khi xử lý JSON: {e}")
            error_message = json.dumps({"error": str(e)}).encode()
            
            response = "HTTP/1.1 500 Internal Server Error\r\n"
            response += "Content-Type: application/json\r\n"
            response += f"Content-Length: {len(error_message)}\r\n"
            response += "Connection: close\r\n\r\n"
            
            # Kết hợp headers và nội dung thành một message duy nhất
            complete_response = response.encode() + error_message
            
            # Gửi toàn bộ response trong một lần
            client.sendall(complete_response)
    
    def serve_404(self, client):
        """Phục vụ trang 404"""
        message = "404 Not Found"
        
        response = "HTTP/1.1 404 Not Found\r\n"
        response += "Content-Type: text/plain\r\n"
        response += f"Content-Length: {len(message)}\r\n"
        response += "Connection: close\r\n\r\n"
        response += message
        
        client.send(response.encode())
    
    def get_html_template(self):
        """Trả về template HTML cho trang giám sát"""
        return """
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
            <title>Hệ Thống Giám Sát IoT</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f0f0f0;
                    font-size: 16px;
                }
                .container {
                    max-width: 1000px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                    text-align: center;
                    font-size: 24px;
                }
                .panel {
                    margin-bottom: 20px;
                    padding: 15px;
                    border-radius: 5px;
                    background-color: #fff;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                .section {
                    margin-bottom: 20px;
                }
                h2, h3 {
                    color: #333;
                    margin-top: 0;
                }
                .sensor-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }
                .sensor-card {
                    background-color: #f9f9f9;
                    border-radius: 5px;
                    padding: 15px;
                    text-align: center;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                .sensor-card h3 {
                    margin-top: 0;
                    font-size: 16px;
                    color: #555;
                }
                .sensor-card p {
                    font-size: 24px;
                    font-weight: bold;
                    margin: 10px 0 0 0;
                    color: #007bff;
                }
                .sensor-value {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 10px;
                    padding: 5px 0;
                    border-bottom: 1px solid #eee;
                }
                .sensor-label {
                    color: #555;
                    font-weight: bold;
                }
                .alert {
                    background-color: #ffcccc;
                    color: #cc0000;
                    padding: 10px 15px;
                    border-radius: 5px;
                    margin-bottom: 15px;
                    display: none;
                }
                
                /* Responsive design cho điện thoại di động */
                @media (max-width: 600px) {
                    body {
                        padding: 10px;
                    }
                    .container {
                        padding: 10px;
                    }
                    .sensor-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                    .sensor-card p {
                        font-size: 20px;
                    }
                    h1 {
                        font-size: 20px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Hệ Thống Giám Sát IoT</h1>
                
                <div class="panel">
                    <h2>Cảnh Báo</h2>
                    <div id="alert-temp1" class="alert">Cảnh báo: Nhiệt độ cảm biến 1 vượt ngưỡng!</div>
                    <div id="alert-temp2" class="alert">Cảnh báo: Nhiệt độ cảm biến 2 vượt ngưỡng!</div>
                    <div id="alert-water" class="alert">Cảnh báo: Mực nước vượt ngưỡng!</div>
                </div>
                
                <div class="panel">
                    <h2>Dữ Liệu Cảm Biến</h2>
                    <div class="sensor-grid">
                        <div class="sensor-card">
                            <h3>Nhiệt Độ #1</h3>
                            <p id="temp1">Đang tải...</p>
                        </div>
                        <div class="sensor-card">
                            <h3>Nhiệt Độ #2</h3>
                            <p id="temp2">Đang tải...</p>
                        </div>
                        <div class="sensor-card">
                            <h3>Nhiệt Độ Phòng</h3>
                            <p id="room-temp">Đang tải...</p>
                        </div>
                        <div class="sensor-card">
                            <h3>Độ Ẩm</h3>
                            <p id="humidity">Đang tải...</p>
                        </div>
                        <div class="sensor-card">
                            <h3>Mực Nước</h3>
                            <p id="water-level">Đang tải...</p>
                        </div>
                        <div class="sensor-card">
                            <h3>Thể Tích</h3>
                            <p id="tank-volume">Đang tải...</p>
                        </div>
                    </div>
                </div>
                
                <!-- Thêm phần hiển thị thời gian cập nhật -->
                <div class="section" style="margin-top: 20px; text-align: center; background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
                    <h3>Thông tin hệ thống</h3>
                    <div class="sensor-value">
                        <div class="sensor-label">Thời gian cập nhật gần nhất:</div>
                        <p id="last-update">Đang tải...</p>
                    </div>
                    <div class="sensor-value">
                        <div class="sensor-label">Chu kỳ cập nhật:</div>
                        <p id="update-interval">60 giây</p>
                    </div>
                </div>
            </div>
            
            <script>
                // Biến theo dõi trạng thái cập nhật
                let lastUpdateTime = 0;
                let updateInterval = 10000; // 10 giây
                
                // Thêm thông báo trạng thái cập nhật
                let statusContainer = document.createElement('div');
                statusContainer.style.position = 'fixed';
                statusContainer.style.bottom = '20px';
                statusContainer.style.left = '50%';
                statusContainer.style.transform = 'translateX(-50%)';
                statusContainer.style.backgroundColor = 'rgba(0,0,0,0.7)';
                statusContainer.style.color = 'white';
                statusContainer.style.padding = '10px 20px';
                statusContainer.style.borderRadius = '20px';
                statusContainer.style.zIndex = '1000';
                statusContainer.style.fontSize = '14px';
                statusContainer.style.display = 'none';
                document.body.appendChild(statusContainer);
                
                // Hiển thị thông báo
                function showStatus(message, isError = false) {
                    statusContainer.textContent = message;
                    statusContainer.style.backgroundColor = isError ? 'rgba(200,0,0,0.8)' : 'rgba(0,0,0,0.7)';
                    statusContainer.style.display = 'block';
                    
                    // Tự động ẩn sau 3 giây
                    setTimeout(() => {
                        statusContainer.style.display = 'none';
                    }, 3000);
                }
                
                // Hàm cập nhật dữ liệu từ server
                function updateData() {
                    showStatus('Đang cập nhật dữ liệu...');
                    
                    fetch('/data')
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`Lỗi HTTP: ${response.status}`);
                            }
                            return response.json();
                        })
                        .then(data => {
                            // Cập nhật dữ liệu trên trang
                            document.getElementById('temp1').textContent = (data.temp1 != null) ? data.temp1.toFixed(1) + '°C' : 'N/A';
                            document.getElementById('temp2').textContent = (data.temp2 != null) ? data.temp2.toFixed(1) + '°C' : 'N/A';
                            document.getElementById('room-temp').textContent = (data.room_temp != null) ? data.room_temp.toFixed(1) + '°C' : 'N/A';
                            document.getElementById('humidity').textContent = (data.humidity != null) ? data.humidity.toFixed(1) + '%' : 'N/A';
                            document.getElementById('water-level').textContent = (data.water_level != null) ? data.water_level.toFixed(2) + 'm' : 'N/A';
                            document.getElementById('tank-volume').textContent = (data.tank_volume != null) ? data.tank_volume.toFixed(1) + 'L' : 'N/A';
                            
                            // Cập nhật thời gian cập nhật gần nhất
                            document.getElementById('last-update').textContent = data.timestamp || 'Không có dữ liệu';
                            
                            // Hiển thị cảnh báo nếu có
                            if (data.alerts) {
                                document.getElementById('alert-temp1').style.display = data.alerts.temp1 ? 'block' : 'none';
                                document.getElementById('alert-temp2').style.display = data.alerts.temp2 ? 'block' : 'none';
                                document.getElementById('alert-water').style.display = data.alerts.water_level ? 'block' : 'none';
                            }
                            
                            lastUpdateTime = Date.now();
                            showStatus('Đã cập nhật dữ liệu thành công');
                        })
                        .catch(error => {
                            console.error('Lỗi khi lấy dữ liệu:', error);
                            showStatus('Lỗi khi cập nhật dữ liệu', true);
                        });
                }
                
                // Cập nhật dữ liệu ngay khi trang được tải
                window.addEventListener('load', function() {
                    // Kiểm tra nếu initialSensorData đã được cung cấp từ server
                    if (typeof initialSensorData !== 'undefined') {
                        // Cập nhật UI với dữ liệu ban đầu
                        document.getElementById('temp1').textContent = (initialSensorData.temp1 != null) ? initialSensorData.temp1.toFixed(1) + '°C' : 'N/A';
                        document.getElementById('temp2').textContent = (initialSensorData.temp2 != null) ? initialSensorData.temp2.toFixed(1) + '°C' : 'N/A';
                        document.getElementById('room-temp').textContent = (initialSensorData.room_temp != null) ? initialSensorData.room_temp.toFixed(1) + '°C' : 'N/A';
                        document.getElementById('humidity').textContent = (initialSensorData.humidity != null) ? initialSensorData.humidity.toFixed(1) + '%' : 'N/A';
                        document.getElementById('water-level').textContent = (initialSensorData.water_level != null) ? initialSensorData.water_level.toFixed(2) + 'm' : 'N/A';
                        document.getElementById('tank-volume').textContent = (initialSensorData.tank_volume != null) ? initialSensorData.tank_volume.toFixed(1) + 'L' : 'N/A';
                        
                        // Cập nhật thời gian cập nhật gần nhất
                        document.getElementById('last-update').textContent = initialSensorData.timestamp || 'Không có dữ liệu';
                        
                        if (initialSensorData.alerts) {
                            document.getElementById('alert-temp1').style.display = initialSensorData.alerts.temp1 ? 'block' : 'none';
                            document.getElementById('alert-temp2').style.display = initialSensorData.alerts.temp2 ? 'block' : 'none';
                            document.getElementById('alert-water').style.display = initialSensorData.alerts.water_level ? 'block' : 'none';
                        }
                        
                        showStatus('Dữ liệu ban đầu đã được tải');
                    } else {
                        // Tải dữ liệu từ API nếu không có dữ liệu ban đầu
                        updateData();
                    }
                    
                    // Thiết lập cập nhật định kỳ
                    setInterval(updateData, updateInterval);
                    
                    // Thêm nút làm mới thủ công
                    let refreshButton = document.createElement('button');
                    refreshButton.textContent = 'Làm mới dữ liệu';
                    refreshButton.style.display = 'block';
                    refreshButton.style.margin = '20px auto';
                    refreshButton.style.padding = '10px 20px';
                    refreshButton.style.backgroundColor = '#007bff';
                    refreshButton.style.color = 'white';
                    refreshButton.style.border = 'none';
                    refreshButton.style.borderRadius = '5px';
                    refreshButton.style.cursor = 'pointer';
                    refreshButton.onclick = updateData;
                    
                    document.querySelector('.container').appendChild(refreshButton);
                });
            </script>
        </body>
        </html>
        """


