import re
import unicodedata
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from contextlib import contextmanager
import logging
import atexit

logger = logging.getLogger(__name__)

# Biến toàn cục để lưu trữ driver instance
_driver = None

def get_driver():
    """Singleton pattern để tái sử dụng Chrome driver."""
    global _driver
    if _driver is None:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-site-isolation-trials')
        chrome_options.page_load_strategy = 'eager'
        
        service = Service(ChromeDriverManager().install())
        _driver = webdriver.Chrome(service=service, options=chrome_options)
        _driver.set_page_load_timeout(30)
        
        # Đăng ký hàm cleanup khi thoát
        atexit.register(cleanup_driver)
        
    return _driver

def cleanup_driver():
    """Dọn dẹp driver khi thoát."""
    global _driver
    if _driver:
        try:
            _driver.quit()
        except Exception as e:
            logger.error(f"Lỗi khi đóng ChromeDriver: {str(e)}")
        _driver = None

class ChromeDriverManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.driver = None
        return cls._instance
        
    def get_driver(self):
        if self.driver is None:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-extensions')
            options.add_argument('--remote-debugging-port=9222')
            
            self.driver = webdriver.Chrome(options=options)
            
            # Đăng ký hàm cleanup khi thoát
            atexit.register(self.cleanup)
            
        return self.driver
        
    def cleanup(self):
        """Dọn dẹp driver và đóng tất cả tab."""
        if self.driver:
            try:
                # Đóng tất cả tab trừ tab đầu tiên
                if len(self.driver.window_handles) > 1:
                    main_window = self.driver.window_handles[0]
                    for handle in self.driver.window_handles[1:]:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                    self.driver.switch_to.window(main_window)
                
                # Đóng driver
                self.driver.quit()
            except Exception as e:
                logger.error(f"Lỗi khi dọn dẹp Chrome driver: {str(e)}")
            finally:
                self.driver = None

@contextmanager
def get_chrome_driver():
    """Context manager để quản lý Chrome driver."""
    driver_manager = ChromeDriverManager()
    driver = driver_manager.get_driver()
    try:
        # Đóng tất cả tab trừ tab đầu tiên trước khi sử dụng
        if len(driver.window_handles) > 1:
            main_window = driver.window_handles[0]
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(main_window)
            
        yield driver
    except Exception as e:
        logger.error(f"Lỗi khi sử dụng Chrome driver: {str(e)}")
        raise
    finally:
        # Đóng các tab phụ sau khi sử dụng
        if len(driver.window_handles) > 1:
            main_window = driver.window_handles[0]
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(main_window)

def standardize_product_name(name):
    """Chuẩn hóa tên sản phẩm."""
    if not name:
        return ""
    # Mapping tiếng Việt
    vietnamese_map = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y'
    }
    
    # Chuyển về chữ thường và chuẩn hóa Unicode
    name = unicodedata.normalize('NFKD', name.lower())
    
    # Thay thế các ký tự tiếng Việt
    for vietnamese, latin in vietnamese_map.items():
        name = name.replace(vietnamese, latin)
    
    # Loại bỏ các ký tự không phải chữ cái, số hoặc khoảng trắng
    name = re.sub(r'[^\w\s-]', '', name)
    
    # Loại bỏ khoảng trắng thừa
    name = ' '.join(name.split())
    
    return name

def get_category_id_from_keyword(keyword):
    """Lấy ID danh mục từ từ khóa."""
    keyword = keyword.lower()
    if any(x in keyword for x in ["điện thoại", "phone", "iphone", "samsung", "oppo", "xiaomi"]):
        return 1
    elif any(x in keyword for x in ["laptop", "macbook", "notebook"]):
        return 2
    elif any(x in keyword for x in ["tablet", "ipad", "máy tính bảng"]):
        return 3
    return None

def extract_price(price_text):
    """
    Trích xuất giá từ text:
    - Bỏ các ký tự không phải số
    - Chuyển về kiểu float
    """
    if not price_text:
        return 0.0
    try:
        price = ''.join(c for c in price_text if c.isdigit() or c == '.')
        return float(price)
    except:
        return 0.0

def clean_url(url, base_url=None):
    """
    Chuẩn hóa URL:
    - Thêm base_url nếu là relative URL
    - Bỏ các query params không cần thiết
    """
    if not url:
        return ""
    
    url = url.split('?')[0]
    
    if base_url and not url.startswith(('http://', 'https://')):
        return f"{base_url.rstrip('/')}/{url.lstrip('/')}"
    
    return url

def get_store_name(store_id):
    """
    Lấy tên store từ ID
    """
    store_names = {
        1: "Điện Máy Xanh",
        2: "Thế Giới Di Động",
        3: "Chợ Tốt"
    }
    return store_names.get(store_id, "Unknown")

def validate_image_url(url):
    """
    Validate and clean image URLs:
    - Check if URL is valid
    - Ensure URL uses HTTPS
    - Verify common image extensions
    """
    if not url:
        return ""
    
    # Clean the URL
    url = url.strip()
    
    # Convert HTTP to HTTPS
    if url.startswith("http://"):
        url = "https://" + url[7:]
    
    # Add https:// if missing
    if url.startswith("//"):
        url = "https:" + url
        
    # Validate URL format
    if not url.startswith(("https://", "http://")):
        return ""
        
    # Check for common image extensions
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    if not any(url.lower().endswith(ext) for ext in valid_extensions):
        # If no extension, check if URL contains image-like paths
        image_indicators = ('image', 'img', 'photo', 'picture', 'thumb')
        if not any(indicator in url.lower() for indicator in image_indicators):
            return ""
            
    return url

def setup_chrome_driver():
    """Thiết lập và trả về Chrome options với các cấu hình tối ưu."""
    options = Options()
    options.add_argument('--headless')  # Chạy ở chế độ headless
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    
    # Thêm các tùy chọn để tránh phát hiện automation
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Thêm User-Agent để giả lập trình duyệt thật
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    # Tối ưu hiệu suất
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-site-isolation-trials')
    options.page_load_strategy = 'eager'
    
    return options