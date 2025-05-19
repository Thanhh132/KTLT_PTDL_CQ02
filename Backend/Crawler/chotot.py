import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import re
from urllib.parse import urljoin
from .utils import standardize_product_name, get_category_id_from_keyword, validate_image_url

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

def crawl_chotot(product_name):
    product_name_lower = standardize_product_name(product_name)
    search_query = product_name.replace(' ', '%20')
    results = []
    page = 1
    limit = 20
    max_pages = 2

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.chotot.com",
        "Referer": "https://www.chotot.com/",
        "Connection": "keep-alive"
    }

    while page <= max_pages:
        try:
            api_url = f"https://gateway.chotot.com/v1/public/ad-listing?cg=&st=s,k&limit={limit}&o={(page-1)*limit}&q={search_query}"
            logger.info(f"Crawling Chợ Tốt API page {page}: {api_url}")
            
            response = session.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('ads', [])
            if not items:
                logger.info("Không tìm thấy thêm sản phẩm")
                break

            for item in items:
                try:
                    name = item.get('subject', '')
                    if not name:
                        continue

                    price = item.get('price', 0)
                    price = int(price) if price else 0
                    if price <= 0:
                        continue

                    list_id = item.get('list_id', '')
                    link = f"https://www.chotot.com/{list_id}.htm" if list_id else ""
                    if not link:
                        continue

                    image_url = item.get('image', '') or (item.get('images', [])[0] if item.get('images', []) else '')
                    image_url = validate_image_url(image_url)

                    product = {
                        "name": name,
                        "store_id": 3,  # Chợ Tốt
                        "store_name": "Chợ Tốt",
                        "category_id": get_category_id_from_keyword(name),
                        "price": price,
                        "rating": 0.0,
                        "link": link,
                        "image_url": image_url
                    }
                    results.append(product)
                    logger.debug(f"Thêm sản phẩm: {name}")
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý sản phẩm: {str(e)}")
                    continue

            if len(items) < limit:
                break
            page += 1

        except requests.RequestException as e:
            logger.error(f"Lỗi khi truy cập API Chợ Tốt: {str(e)}")
            break

    logger.info(f"Đã crawl {len(results)} sản phẩm từ Chợ Tốt")
    return results