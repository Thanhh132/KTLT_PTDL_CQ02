# Ứng dụng So sánh giá sản phẩm

Ứng dụng web cho phép tìm kiếm và so sánh giá sản phẩm từ các trang thương mại điện tử lớn tại Việt Nam.

## Yêu cầu hệ thống

- Python 3.8 trở lên
- SQL Server
- SQL Server ODBC Driver 17
- Google Chrome và ChromeDriver
- Các gói Python được liệt kê trong `requirements.txt`

## Cài đặt

1. Clone repository:
```bash
git clone <repository_url>
cd <repository_name>
```

2. Tạo và kích hoạt môi trường ảo:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Cài đặt các gói phụ thuộc:
```bash
pip install -r requirements.txt
```

4. Tải và cài đặt ChromeDriver:
- Tải ChromeDriver từ [trang chính thức](https://sites.google.com/chromium.org/driver/)
- Đặt file chromedriver.exe vào thư mục gốc của dự án

5. Tạo file `.env` với nội dung sau:
```
DB_DRIVER={ODBC Driver 17 for SQL Server}
DB_SERVER=<tên_server_sql>
DB_NAME=TMDT_New
CHROME_DRIVER_PATH=chromedriver.exe
API_HOST=127.0.0.1
API_PORT=8000
```

## Chạy ứng dụng

1. Khởi động server:
```bash
cd Backend
python main.py
```

2. Truy cập ứng dụng:
- Mở trình duyệt và truy cập `http://127.0.0.1:8000`

## Tính năng

- Tìm kiếm sản phẩm trên nhiều trang thương mại điện tử
- So sánh giá từ các nguồn khác nhau
- Hiển thị thông tin chi tiết sản phẩm
- Lưu lịch sử giá sản phẩm

## Cấu trúc dự án

```
├── Backend/
│   ├── Crawler/         # Các module crawler
│   ├── Database/        # Xử lý database
│   ├── Services/        # Logic nghiệp vụ
│   └── main.py         # Entry point
├── Frontend/
│   ├── CSS/
│   ├── JS/
│   └── index.html
├── requirements.txt
└── README.md
```

## Nguồn dữ liệu

- Điện Máy Xanh
- Thế Giới Di Động
- Nguyễn Kim
- Chợ Tốt 