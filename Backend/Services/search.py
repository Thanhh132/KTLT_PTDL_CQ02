import threading
import logging
import re
import unicodedata
from Database.db import init_db, save_products, get_db_cursor
from Crawler.dienmayxanh import crawl_dienmayxanh
from Crawler.thegioididong import crawl_thegioididong
from Crawler.chotot import crawl_chotot
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import concurrent.futures
from urllib.parse import urljoin
from datetime import datetime
from unidecode import unidecode

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Định nghĩa từ khóa cho các danh mục sản phẩm
required_keywords = {
    1: {  # Điện thoại
        "keywords": ["dien thoai", "smartphone", "iphone", "samsung", "xiaomi", "oppo", "vivo", "realme", "nokia", "huawei"],
        "name": "Điện thoại"
    },
    2: {  # Laptop
        "keywords": ["laptop", "macbook", "dell", "hp", "asus", "lenovo", "acer", "msi", "lg gram"],
        "name": "Laptop"
    },
    3: {  # Máy tính bảng
        "keywords": ["may tinh bang", "tablet", "ipad", "samsung tab", "xiaomi pad", "huawei matepad"],
        "name": "Máy tính bảng"
    },
    4: {  # Tai nghe
        "keywords": ["tai nghe", "headphone", "earphone", "airpods", "sony", "bluetooth", "true wireless"],
        "name": "Tai nghe"
    },
    5: {  # Tivi
        "keywords": ["tivi", "tv", "smart tv", "samsung tv", "lg tv", "tcl", "sony tv"],
        "name": "Tivi"
    },
    6: {  # Máy hút bụi
        "keywords": ["may hut bui", "máy hút bụi", "vacuum", "robot hút bụi", "máy lau nhà", "dyson", "electrolux"],
        "name": "Máy hút bụi"
    },
    7: {  # Máy giặt
        "keywords": ["may giat", "máy giặt", "washing machine", "lg", "samsung", "electrolux", "panasonic"],
        "name": "Máy giặt"
    },
    8: {  # Tủ lạnh
        "keywords": ["tu lanh", "tủ lạnh", "refrigerator", "side by side", "mini", "inverter"],
        "name": "Tủ lạnh"
    },
    9: {  # Điều hòa
        "keywords": ["dieu hoa", "điều hòa", "máy lạnh", "air conditioner", "inverter"],
        "name": "Điều hòa"
    },
    10: {  # Nồi cơm điện
        "keywords": ["noi com dien", "nồi cơm điện", "rice cooker", "toshiba", "sharp", "cuckoo"],
        "name": "Nồi cơm điện"
    },
    11: {  # Khác
        "keywords": [],
        "name": "Khác"
    }
}

# Định nghĩa danh mục sản phẩm cho từng store - cho phép crawl tất cả
store_categories = {
    1: set(range(1, 12)),  # Điện Máy Xanh - tất cả danh mục từ 1-11
    2: set(range(1, 12)),  # Thế Giới Di Động - tất cả danh mục từ 1-11
    3: set(range(1, 12)),  # Chợ Tốt - tất cả danh mục từ 1-11
}

class ResultCollector:
    def __init__(self):
        self.results = []
        self.lock = threading.Lock()

    def add_results(self, results):
        with self.lock:
            self.results.extend(results)

    def get_results(self):
        return self.results

def normalize_text(text: str) -> str:
    """Chuẩn hóa text để so sánh"""
    # Chuyển về chữ thường và bỏ dấu
    text = unidecode(text.lower())
    # Loại bỏ ký tự đặc biệt
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    # Chuẩn hóa khoảng trắng
    return ' '.join(text.split())

def text_contains(text: str, keywords: str) -> bool:
    """Kiểm tra xem text có chứa keywords hay không."""
    if not text or not keywords:
        return False
    text = normalize_text(text)
    keywords = normalize_text(keywords)
    return all(keyword in text for keyword in keywords.split())

def crawl_dienmayanh(query: str) -> List[Dict[str, Any]]:
    """Crawl dữ liệu từ Điện Máy Xanh."""
    try:
        url = f"https://www.dienmayxanh.com/tim-kiem?key={query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        # Thêm timeout để tránh treo
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        # Thử các selector khác nhau
        items = (
            soup.select('.product-item') or
            soup.select('.product-list .item') or
            soup.select('.listproduct .item')
        )
        
        if not items:
            logger.warning(f"Không tìm thấy sản phẩm nào trên Điện Máy Xanh với query: {query}")
            return []
            
        for item in items:
            try:
                name = item.select_one('.product-name, h3')
                price = item.select_one('.product-price, .price')
                link = item.select_one('a')
                img = item.select_one('img')
                
                if name and price and link:
                    price_text = price.text.strip().replace('.', '').replace('₫', '').replace('đ', '')
                    price_value = int(re.sub(r'[^\d]', '', price_text))
                    
                    product = {
                        'name': name.text.strip(),
                        'price': price_value,
                        'store_id': 1,  # ID của Điện Máy Xanh
                        'link': urljoin('https://www.dienmayxanh.com', link['href']),
                        'image_url': img['src'] if img and 'src' in img.attrs else None,
                        'condition': 'new',  # Sản phẩm từ DMX luôn là mới
                        'category_id': get_product_category(name.text.strip()) or 'Chưa phân loại',
                        'rating': None  # Chưa có đánh giá
                    }
                    products.append(product)
            except Exception as e:
                logger.error(f"Lỗi khi xử lý sản phẩm từ Điện Máy Xanh: {str(e)}")
                continue
                
        return products
    except requests.Timeout:
        logger.error("Timeout khi crawl Điện Máy Xanh")
        return []
    except requests.RequestException as e:
        logger.error(f"Lỗi kết nối khi crawl Điện Máy Xanh: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Lỗi không xác định khi crawl Điện Máy Xanh: {str(e)}")
        return []

def crawl_tgdd(query: str) -> List[Dict[str, Any]]:
    """Crawl dữ liệu từ Thế Giới Di Động."""
    try:
        url = f"https://www.thegioididong.com/tim-kiem?key={query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        # Thêm timeout để tránh treo
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        # Thử các selector khác nhau
        items = (
            soup.select('.item') or
            soup.select('.product-item') or
            soup.select('.product__item')
        )
        
        if not items:
            logger.warning(f"Không tìm thấy sản phẩm nào trên TGDĐ với query: {query}")
            return []
            
        for item in items:
            try:
                name = item.select_one('h3, .product-name')
                price = item.select_one('.price, .product-price')
                link = item.select_one('a')
                img = item.select_one('img')
                
                if name and price and link:
                    price_text = price.text.strip().replace('.', '').replace('₫', '').replace('đ', '')
                    price_value = int(re.sub(r'[^\d]', '', price_text))
                    
                    product = {
                        'name': name.text.strip(),
                        'price': price_value,
                        'store_id': 2,  # ID của Thế Giới Di Động
                        'link': urljoin('https://www.thegioididong.com', link['href']),
                        'image_url': img['src'] if img and 'src' in img.attrs else None,
                        'condition': 'new',  # Sản phẩm từ TGDD luôn là mới
                        'category_id': get_product_category(name.text.strip()) or 'Chưa phân loại',
                        'rating': None  # Chưa có đánh giá
                    }
                    products.append(product)
            except Exception as e:
                logger.error(f"Lỗi khi xử lý sản phẩm từ TGDĐ: {str(e)}")
                continue
                
        return products
    except requests.Timeout:
        logger.error("Timeout khi crawl TGDĐ")
        return []
    except requests.RequestException as e:
        logger.error(f"Lỗi kết nối khi crawl TGDĐ: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Lỗi không xác định khi crawl TGDĐ: {str(e)}")
        return []

def run_crawler(crawler_func, product_name, source_name, collector):
    """Chạy crawler và thu thập kết quả."""
    try:
        logger.debug(f"Khởi chạy crawler {source_name} với từ khóa: {product_name}")
        
        # Gọi hàm crawler tương ứng
        if source_name == "Điện Máy Xanh":
            results = crawl_dienmayxanh(product_name)
        elif source_name == "Thế Giới Di Động":
            results = crawl_thegioididong(product_name)
        else:
            results = crawler_func(product_name)
        
        if results:
            # Thêm store_id vào mỗi sản phẩm
            for product in results:
                if source_name == "Điện Máy Xanh":
                    product['store_id'] = 1
                elif source_name == "Thế Giới Di Động":
                    product['store_id'] = 2
                elif source_name == "Chợ Tốt":
                    product['store_id'] = 3
                    
                # Thêm category_id dựa trên tên sản phẩm
                product['category_id'] = get_product_category(product['name'])
            
            collector.add_results(results)
            logger.info(f"Crawler {source_name} hoàn thành, thu thập được {len(results)} sản phẩm")
        else:
            logger.info(f"Crawler {source_name} không tìm thấy kết quả nào")
            
    except Exception as e:
        logger.error(f"Lỗi khi chạy crawler {source_name}: {str(e)}")

def get_product_category(product_name):
    """Xác định danh mục sản phẩm dựa trên tên."""
    if not product_name:
        return 11  # Trả về ID của danh mục "Khác"
        
    normalized_name = normalize_text(product_name)
    
    # Kiểm tra từng danh mục
    for category_id, category_info in required_keywords.items():
        # Bỏ qua danh mục "Khác"
        if category_id == 11:
            continue
            
        # Kiểm tra xem tên sản phẩm có chứa bất kỳ từ khóa nào của danh mục
        if any(keyword.lower() in normalized_name for keyword in category_info["keywords"]):
            return category_id
            
    # Nếu không thuộc danh mục nào, trả về ID của danh mục "Khác"
    return 11

def should_crawl_store(store_id, category_id):
    """Luôn cho phép crawl từ mọi store."""
    return True

def search_official_stores(product_name, collector):
    """Tìm kiếm trên Điện Máy Xanh và Thế Giới Di Động."""
    logger.info("Bắt đầu tìm kiếm trên các cửa hàng chính thức")

    # Chạy tất cả crawler
    crawlers = [
        (crawl_dienmayxanh, "Điện Máy Xanh"),
        (crawl_thegioididong, "Thế Giới Di Động")
    ]

    threads = []
    for crawler_func, source_name in crawlers:
        thread = threading.Thread(
            target=run_crawler,
            args=(crawler_func, product_name, source_name, collector)
        )
        threads.append(thread)
        thread.start()
        logger.info(f"Đã khởi chạy crawler cho {source_name}")

    for thread in threads:
        thread.join()

def search_chotot(product_name, collector):
    """Tìm kiếm trên Chợ Tốt."""
    try:
        logger.info("Bắt đầu tìm kiếm trên Chợ Tốt")
        results = crawl_chotot(product_name)
        if results:
            # Thêm store_id và category_id cho mỗi sản phẩm
            for product in results:
                product['store_id'] = 3
                product['category_id'] = get_product_category(product['name'])
            collector.add_results(results)
        logger.info(f"Hoàn thành tìm kiếm trên Chợ Tốt, thu được {len(results)} kết quả")
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm trên Chợ Tốt: {str(e)}")

def search_in_database(query: str, min_price: float = None, max_price: float = None, sort_order: str = 'asc'):
    """
    Tìm kiếm sản phẩm trong database với khả năng tìm kiếm linh hoạt
    Args:
        query (str): Từ khóa tìm kiếm
        min_price (float, optional): Giá tối thiểu. Defaults to None.
        max_price (float, optional): Giá tối đa. Defaults to None.
        sort_order (str, optional): Thứ tự sắp xếp giá ('asc' hoặc 'desc'). Defaults to 'asc'.
    """
    try:
        with get_db_cursor() as cursor:
            sql = """
                SELECT p.*, s.name as store_name
                FROM Products p
                JOIN Stores s ON p.store_id = s.id
                WHERE 1=1
            """
            params = []

            # Thêm điều kiện tìm kiếm theo từ khóa
            if query:
                normalized_query = normalize_text(query)
                search_terms = normalized_query.split()
                
                if search_terms:
                    sql += " AND ("
                    term_conditions = []
                    
                    for term in search_terms:
                        # Tìm kiếm chính xác
                        term_conditions.append("LOWER(p.name) LIKE ?")
                        params.append(f"%{term}%")
                        
                        # Tìm kiếm với dấu cách
                        term_conditions.append("LOWER(p.name) LIKE ?")
                        params.append(f"% {term} %")
                        
                        # Tìm kiếm đầu từ
                        term_conditions.append("LOWER(p.name) LIKE ?")
                        params.append(f"{term}%")
                        
                        # Tìm kiếm theo từ đồng nghĩa
                        related_terms = get_related_terms(term)
                        for related_term in related_terms:
                            term_conditions.append("LOWER(p.name) LIKE ?")
                            params.append(f"%{related_term}%")
                    
                    sql += " OR ".join(term_conditions) + ")"

            # Thêm điều kiện giá nếu có
            if min_price is not None:
                sql += " AND p.price >= ?"
                params.append(min_price)
            if max_price is not None:
                sql += " AND p.price <= ?"
                params.append(max_price)

            # Sắp xếp kết quả theo độ phù hợp và giá
            sql += """
                ORDER BY 
                    CASE 
                        WHEN LOWER(p.name) LIKE ? THEN 3  -- Khớp chính xác
                        WHEN LOWER(p.name) LIKE ? THEN 2  -- Chứa từ khóa ở đầu
                        ELSE 1                            -- Chứa từ khóa ở bất kỳ đâu
                    END DESC,
                    p.price {}
            """.format('ASC' if sort_order.lower() == 'asc' else 'DESC')
            
            # Thêm tham số cho ORDER BY
            params.extend([f"%{normalized_query}%", f"{normalized_query}%"])

            # Thực thi truy vấn
            cursor.execute(sql, params)
            
            # Chuyển kết quả thành list of dict
            columns = [column[0] for column in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                product = dict(zip(columns, row))
                # Chuyển đổi decimal sang float cho JSON serialization
                if 'price' in product:
                    product['price'] = float(product['price'])
                results.append(product)

            return {
                "query": query,
                "total": len(results),
                "results": results,
                "filters": {
                    "min_price": min(p['price'] for p in results) if results else None,
                    "max_price": max(p['price'] for p in results) if results else None,
                    "stores": list(set(p['store_name'] for p in results)),
                    "sort_order": sort_order
                }
            }

    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm trong database: {str(e)}")
        return {
            "query": query,
            "total": 0,
            "results": [],
            "error": str(e)
        }

def get_related_terms(term: str) -> list:
    """
    Lấy các từ đồng nghĩa hoặc từ liên quan
    Ví dụ: phone -> điện thoại, smartphone, dt, dien thoai
    """
    related_terms_dict = {
        'phone': ['điện thoại', 'smartphone', 'dt', 'dien thoai'],
        'laptop': ['máy tính xách tay', 'notebook', 'may tinh xach tay'],
        'tablet': ['máy tính bảng', 'may tinh bang', 'mtb'],
        'tv': ['tivi', 'television', 'smart tv'],
        'refrigerator': ['tủ lạnh', 'tu lanh'],
        'washing': ['máy giặt', 'may giat'],
        'headphone': ['tai nghe', 'earphone', 'airpod'],
        'speaker': ['loa', 'speaker'],
        'camera': ['máy ảnh', 'may anh'],
        'printer': ['máy in', 'may in'],
        'mouse': ['chuột', 'chuot'],
        'keyboard': ['bàn phím', 'ban phim'],
    }
    
    # Chuẩn hóa term
    term_lower = term.lower()
    
    # Tìm trong từ điển
    for key, values in related_terms_dict.items():
        if term_lower in [key] + values:
            return list(set(values + [key]) - {term_lower})
    
    return []

def is_relevant_product(product_name, search_query):
    """Kiểm tra xem sản phẩm có phù hợp với từ khóa tìm kiếm không"""
    normalized_name = normalize_text(product_name)
    normalized_query = normalize_text(search_query)
    
    # Kiểm tra các trường hợp:
    # 1. Tên sản phẩm chứa từ khóa
    # 2. Từ khóa chứa tên sản phẩm
    # 3. Độ tương đồng của các từ
    if normalized_query in normalized_name or normalized_name in normalized_query:
        return True
        
    # Tách thành các từ để so sánh
    query_words = set(normalized_query.split())
    name_words = set(normalized_name.split())
    
    # Tính số từ khớp
    matching_words = query_words.intersection(name_words)
    
    # Nếu có ít nhất 50% số từ khớp, coi là phù hợp
    return len(matching_words) >= len(query_words) * 0.5

def search_product(query):
    """
    Tìm kiếm sản phẩm từ các nguồn và lưu vào database
    """
    try:
        results = []
        
        # Tìm kiếm trên Điện Máy Xanh
        dmx_results = crawl_dienmayxanh(query)
        if dmx_results:
            # Tin tưởng kết quả từ Điện Máy Xanh
            results.extend(dmx_results)
            
        # Tìm kiếm trên Thế Giới Di Động
        tgdd_results = crawl_thegioididong(query)
        if tgdd_results:
            # Tin tưởng kết quả từ Thế Giới Di Động
            results.extend(tgdd_results)
            
        # Tìm kiếm trên Chợ Tốt
        ct_results = crawl_chotot(query)
        if ct_results:
            # Lọc kết quả từ Chợ Tốt để đảm bảo độ chính xác
            filtered_ct = [
                product for product in ct_results 
                if is_relevant_product(product['name'], query)
            ]
            results.extend(filtered_ct)
        
        # Lưu kết quả vào database
        save_products(results, query)
        
        return {
            "total": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm sản phẩm: {str(e)}")
        return {"total": 0, "results": []}

def load_database_to_web():
    """Tải toàn bộ sản phẩm từ database."""
    try:
        with get_db_cursor() as cursor:
            # Truy vấn với xử lý tên cửa hàng
            sql = """
                SELECT 
                    p.*,
                    CASE s.id
                        WHEN 1 THEN N'Điện Máy Xanh'
                        WHEN 2 THEN N'Thế Giới Di Động'
                        WHEN 3 THEN N'Chợ Tốt'
                        ELSE s.name
                    END as store_name
                FROM Products p
                JOIN Stores s ON p.store_id = s.id
                ORDER BY p.last_updated DESC
            """
            cursor.execute(sql)
            
            # Lấy tên cột và dữ liệu
            columns = [column[0] for column in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                product = dict(zip(columns, row))
                
                # Chuyển đổi decimal sang float cho JSON serialization
                if 'price' in product:
                    product['price'] = float(product['price'])
                
                results.append(product)
            
            logger.info(f"Đã tải {len(results)} sản phẩm từ database")
            return {
                "total": len(results),
                "results": results
            }
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu từ database: {str(e)}")
        return {"total": 0, "results": []}