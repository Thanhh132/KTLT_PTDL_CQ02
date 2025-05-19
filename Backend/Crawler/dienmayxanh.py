from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, SessionNotCreatedException
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
import logging
from urllib.parse import urljoin
import re
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from .utils import validate_image_url, setup_chrome_driver

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_url(url, base_url=""):
    """Làm sạch URL, thêm base_url nếu cần."""
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = urljoin(base_url, url)
    elif not url.startswith(("http://", "https://")):
        url = urljoin(base_url, url)
    return url

def standardize_product_name(name):
    """Chuẩn hóa tên sản phẩm."""
    if not name:
        return ""
    # Loại bỏ các ký tự đặc biệt nhưng giữ lại dấu tiếng Việt
    name = re.sub(r'[^\w\s\u0080-\u024F-]', '', name.strip())
    # Chuẩn hóa khoảng trắng
    name = re.sub(r'\s+', ' ', name)
    return name

def extract_price(price_text):
    """Trích xuất giá từ text."""
    try:
        # Loại bỏ các ký tự không phải số
        price_text = re.sub(r'[^\d]', '', price_text)
        return float(price_text) if price_text else 0.0
    except ValueError:
        logger.warning(f"Không thể chuyển đổi giá: {price_text}")
        return 0.0

def get_category_id(product_name):
    """Ánh xạ từ khóa tìm kiếm sang category_id."""
    categories = {
        'dien thoai': 1,  # Điện thoại
        'laptop': 2,      # Laptop
        'may tinh bang': 3,  # Máy tính bảng
        'tai nghe': 4,    # Tai nghe
        'tivi': 5,        # Tivi
        'tu lanh': 6,     # Tủ lạnh
        'may giat': 7     # Máy giặt
    }
    product_name_lower = product_name.lower().strip()
    for keyword, category_id in categories.items():
        if keyword in product_name_lower:
            return category_id
    return None

def crawl_dienmayxanh(product_name):
    base_url = "https://www.dienmayxanh.com/tim-kiem"
    max_products = 50  # Số sản phẩm tối đa sẽ crawl
    products = []
    total_products_found = 0
    last_height = 0
    no_new_products_count = 0
    max_no_new_products = 3  # Số lần tối đa không tìm thấy sản phẩm mới
    
    try:
        # Thiết lập Chrome driver với webdriver-manager
        service = Service(ChromeDriverManager().install())
        options = setup_chrome_driver()
        driver = webdriver.Chrome(service=service, options=options)
        
        logger.info(f"Crawling Điện Máy Xanh: {base_url}")
        
        # Truy cập trang tìm kiếm
        url = f"{base_url}?key={product_name.replace(' ', '+')}"
        
        # Thử lại tối đa 3 lần nếu có lỗi
        for attempt in range(3):
            try:
                driver.get(url)
                # Đợi cho trang load xong
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul.listproduct"))
                )
                break
            except WebDriverException as e:
                logger.warning(f"Thử lại lần {attempt+1} do lỗi: {str(e)}")
                if attempt == 2:  # Lần thử cuối cùng
                    logger.error(f"Không thể crawl {url} sau 3 lần thử")
                    return []
                time.sleep(2)

        # Lấy category_id từ product_name
        category_id = get_category_id(product_name)
        
        # Lưu trữ các sản phẩm đã thêm để tránh trùng lặp
        added_products = set()
        
        # Cuộn trang và thu thập sản phẩm cho đến khi đủ số lượng
        scroll_attempts = 0
        max_scroll_attempts = 10  # Giới hạn số lần cuộn
        
        while (total_products_found < max_products and 
               scroll_attempts < max_scroll_attempts and 
               no_new_products_count < max_no_new_products):
               
            # Lấy chiều cao hiện tại của trang
            current_height = driver.execute_script("return document.body.scrollHeight")
            
            # Cuộn xuống cuối trang
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Đợi để trang load thêm sản phẩm
            
            # Lấy HTML mới sau khi cuộn
            soup = BeautifulSoup(driver.page_source, "html.parser")
            items = soup.select("ul.listproduct li.item")
            
            if not items:
                logger.info("Không tìm thấy sản phẩm nào")
                break
                
            logger.info(f"Tìm thấy {len(items)} mục sản phẩm từ Điện Máy Xanh")
            
            # Đếm số sản phẩm mới trong lần crawl này
            new_products_count = 0
            
            # Xử lý từng sản phẩm
            for item in items:
                if total_products_found >= max_products:
                    logger.info(f"Đã đạt số lượng sản phẩm tối đa ({max_products})")
                    return products
                    
                try:
                    name_elem = item.select_one("h3")
                    price_elem = item.select_one("p.box-price-present, strong.price, .price")
                    link_elem = item.select_one("a")
                    img_elem = item.select_one("img[data-src], img[src]")
                    
                    if not all([name_elem, price_elem, link_elem]):
                        continue
                        
                    name = standardize_product_name(name_elem.text.strip())
                    price = extract_price(price_elem.text)
                    
                    if not name or price <= 0:
                        continue
                        
                    # Tạo key duy nhất cho sản phẩm để tránh trùng lặp
                    product_key = f"{name}_{price}"
                    if product_key in added_products:
                        continue
                        
                    added_products.add(product_key)
                    new_products_count += 1
                    
                    link = clean_url(link_elem.get("href", ""), base_url="https://www.dienmayxanh.com")
                    image_url = clean_url(img_elem.get("data-src", "") or img_elem.get("src", ""), base_url="https://www.dienmayxanh.com") if img_elem else ""
                    image_url = validate_image_url(image_url)

                    products.append({
                        "name": name,
                        "store_id": 1,
                        "store_name": "Điện Máy Xanh",
                        "category_id": category_id or 11,
                        "price": price,
                        "rating": 0.0,
                        "link": link or "",
                        "image_url": image_url,
                        "condition": "new"
                    })
                    total_products_found += 1
                    logger.info(f"Thêm sản phẩm: {name} - {price:,.0f}đ ({total_products_found}/{max_products})")
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý sản phẩm: {str(e)}")
                    continue
            
            # Kiểm tra xem có sản phẩm mới không
            if new_products_count == 0:
                no_new_products_count += 1
                logger.info(f"Không tìm thấy sản phẩm mới lần {no_new_products_count}")
            else:
                no_new_products_count = 0
            
            # Kiểm tra xem đã cuộn đến cuối trang chưa
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                last_height = new_height
            
            # Click nút "Xem thêm" nếu có
            try:
                show_more = driver.find_element(By.CSS_SELECTOR, ".view-more")
                if show_more and show_more.is_displayed():
                    show_more.click()
                    time.sleep(2)
                    scroll_attempts = 0  # Reset scroll attempts sau khi click
                    no_new_products_count = 0  # Reset counter sau khi click
            except:
                pass
        
        if total_products_found == 0:
            logger.warning("Không tìm thấy sản phẩm nào sau khi crawl")
        else:
            logger.info(f"Crawl Điện Máy Xanh thành công: {len(products)} sản phẩm")
        return products
    
    except SessionNotCreatedException as e:
        logger.error(f"Lỗi phiên bản ChromeDriver: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Lỗi khi crawl Điện Máy Xanh: {str(e)}")
        return []
    
    finally:
        if 'driver' in locals():
            driver.quit()