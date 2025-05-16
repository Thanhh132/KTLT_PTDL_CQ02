from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
import logging
from urllib.parse import urljoin
import re
from selenium import webdriver

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
    name = re.sub(r'\s+', ' ', name.strip())
    name = re.sub(r'[^\w\s-]', '', name)
    return name

def get_category_id(product_name):
    """Ánh xạ từ khóa tìm kiếm sang category_id."""
    categories = {
        'dien thoai': 1,  # Điện thoại
        'laptop': 2,      # Laptop
        'may tinh bang': 3,  # Máy tính bảng
        'tai nghe': 4,    # Tai nghe
        'tivi': 5         # Tivi
    }
    product_name_lower = product_name.lower().strip()
    for keyword, category_id in categories.items():
        if keyword in product_name_lower:
            return category_id
    return None

def crawl_thegioididong(product_name):
    url = f"https://www.thegioididong.com/tim-kiem?key={product_name.replace(' ', '+')}"
    max_products = 10
    
    options = Options()
    options.headless = True
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    driver = webdriver.Chrome(options=options)
    
    products = []
    try:
        logger.info(f"Crawling Thế Giới Di Động: {url}")
        for attempt in range(3):
            try:
                driver.get(url)
                time.sleep(5)
                break
            except WebDriverException as e:
                logger.warning(f"Thử lại lần {attempt+1} do lỗi: {str(e)}")
                time.sleep(2)
        else:
            logger.error(f"Không thể crawl {url} sau 3 lần thử")
            return []

        soup = BeautifulSoup(driver.page_source, "html.parser")
        items = soup.select("ul.listproduct li.item")[:max_products]
        logger.info(f"Tìm thấy {len(items)} sản phẩm từ Thế Giới Di Động")
        
        # Lấy category_id từ product_name
        category_id = get_category_id(product_name)
        
        for item in items:
            try:
                name_elem = item.select_one("h3")
                price_elem = item.select_one("strong.price, .price")
                rating_elem = item.select_one("div.ratingresult span")
                link_elem = item.select_one("a")
                img_elem = item.select_one("img[data-src], img[src]")
                
                if name_elem and price_elem and link_elem:
                    name = standardize_product_name(name_elem.text.strip())
                    price_text = price_elem.text.replace("₫", "").replace(".", "").strip()
                    try:
                        price = float(price_text) if price_text.replace(".", "").isdigit() else 0.0
                    except ValueError:
                        logger.warning(f"Không thể chuyển đổi giá: {price_text}")
                        continue
                    if price <= 0:
                        logger.debug(f"Giá không hợp lệ: {price}")
                        continue
                    rating = float(rating_elem.text.split()[0]) if rating_elem else 0.0
                    link = clean_url(link_elem.get("href", ""), base_url="https://www.thegioididong.com")
                    image_url = clean_url(img_elem.get("data-src", "") or img_elem.get("src", ""), base_url="https://www.thegioididong.com") if img_elem else ""
                    
                    if not all([name, link, price]):
                        logger.debug(f"Bỏ qua sản phẩm do thiếu thông tin: {name}")
                        continue

                    products.append({
                        "name": name,
                        "store_id": 2,
                        "store_name": "Thế Giới Di Động",
                        "category_id": category_id,
                        "price": price,
                        "rating": rating,
                        "link": link,
                        "image_url": image_url
                    })
                    logger.info(f"Đã tìm thấy sản phẩm: {name} - {price}đ")
                else:
                    logger.debug("Thiếu thông tin sản phẩm")
            except Exception as e:
                logger.error(f"Lỗi khi xử lý sản phẩm: {str(e)}")
                continue
        
        logger.info(f"Đã crawl được {len(products)} sản phẩm từ Thế Giới Di Động")
        return products
    
    except Exception as e:
        logger.error(f"Lỗi khi crawl Thế Giới Di Động: {str(e)}")
        return []
    
    finally:
        driver.quit()