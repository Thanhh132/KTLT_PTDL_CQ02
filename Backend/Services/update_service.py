from datetime import datetime, timedelta
from Database.db import get_db_cursor
from Services.search import search_product
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from contextlib import contextmanager
import time
import backoff # type: ignore

logger = logging.getLogger(__name__)

@contextmanager
def get_chrome_driver():
    """Context manager để quản lý ChromeDriver session."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.page_load_strategy = 'eager'
    
    service = Service(ChromeDriverManager().install())
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        yield driver
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Lỗi khi đóng ChromeDriver: {str(e)}")

@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=3,
    max_time=300
)
def check_and_update_products():
    """Kiểm tra và cập nhật sản phẩm đã quá 1 ngày với retry mechanism"""
    try:
        with get_db_cursor() as cursor:
            # Lấy các sản phẩm cần cập nhật (đã quá 24h)
            cursor.execute("""
                SELECT TOP 10 id, name, price  -- Giới hạn 10 sản phẩm mỗi lần
                FROM Products 
                WHERE DATEDIFF(hour, last_updated, GETDATE()) >= 24
                ORDER BY last_updated ASC
            """)
            products = cursor.fetchall()
            
            if not products:
                logger.info("Không có sản phẩm nào cần cập nhật")
                return 0
            
            updated_count = 0
            
            with get_chrome_driver() as driver:
                for product_id, product_name, old_price in products:
                    try:
                        # Thêm delay giữa các lần crawl
                        time.sleep(2)
                        
                        # Lưu giá cũ vào lịch sử
                        cursor.execute("""
                            INSERT INTO PriceHistory (product_id, price)
                            SELECT id, price FROM Products WHERE id = ?
                        """, (product_id,))
                        
                        # Cập nhật thông tin mới với timeout
                        new_data = search_product(product_name, driver=driver)
                        
                        if new_data and new_data.get('results'):
                            for item in new_data['results']:
                                if str(item.get('id')) == str(product_id):
                                    new_price = item['price']
                                    
                                    # Kiểm tra nếu giá đã thay đổi
                                    if abs(new_price - old_price) > 1000:  # Chỉ thông báo khi chênh lệch > 1000đ
                                        price_change = new_price - old_price
                                        price_change_percent = (price_change / old_price) * 100
                                        
                                        message = "tăng" if price_change > 0 else "giảm"
                                        notification_text = f"Giá sản phẩm {product_name} đã {message} {abs(price_change_percent):.1f}%"
                                        
                                        cursor.execute("""
                                            INSERT INTO Notifications (product_id, message, price_change, old_price, new_price)
                                            VALUES (?, ?, ?, ?, ?)
                                        """, (product_id, notification_text, price_change, old_price, new_price))
                                        
                                        logger.info(f"Đã tạo thông báo: {notification_text}")
                                    
                                    # Cập nhật giá mới
                                    cursor.execute("""
                                        UPDATE Products 
                                        SET price = ?, last_updated = GETDATE()
                                        WHERE id = ?
                                    """, (new_price, product_id))
                                    updated_count += 1
                                    break
                    except Exception as product_error:
                        logger.error(f"Lỗi khi cập nhật sản phẩm {product_id}: {str(product_error)}")
                        continue
            
            if updated_count > 0:
                logger.info(f"Đã cập nhật {updated_count} sản phẩm")
            return updated_count
            
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật dữ liệu: {str(e)}")
        raise  # Để backoff có thể retry