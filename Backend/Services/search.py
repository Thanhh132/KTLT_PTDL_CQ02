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

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Định nghĩa từ khóa cho các danh mục sản phẩm
required_keywords = {
    "dien thoai": ["dien thoai", "smartphone", "iphone", "samsung", "xiaomi", "oppo", "vivo"],
    "laptop": ["laptop", "macbook", "dell", "hp", "asus", "lenovo", "acer", "msi"],
    "may tinh bang": ["may tinh bang", "tablet", "ipad", "samsung tab"],
    "tai nghe": ["tai nghe", "headphone", "earphone", "airpods", "sony"],
    "tivi": ["tivi", "tv", "smart tv", "samsung tv", "lg tv"],
    "may hut bui": ["may hut bui", "máy hút bụi", "vacuum", "robot hút bụi", "máy lau nhà"],
    "may giat": ["may giat", "máy giặt", "washing machine"],
    "tu lanh": ["tu lanh", "tủ lạnh", "refrigerator"],
    "dieu hoa": ["dieu hoa", "điều hòa", "máy lạnh", "air conditioner"],
    "noi com dien": ["noi com dien", "nồi cơm điện", "rice cooker"]
}

# Định nghĩa danh mục sản phẩm cho từng store
store_categories = {
    1: {  # Điện Máy Xanh
        "dien thoai", "laptop", "may tinh bang", "tivi", "may hut bui", 
        "may giat", "tu lanh", "dieu hoa", "noi com dien"
    },
    2: {  # Thế Giới Di Động
        "dien thoai", "laptop", "may tinh bang", "tai nghe"
    },
    3: {  # Chợ Tốt - hỗ trợ tất cả danh mục
        "dien thoai", "laptop", "may tinh bang", "tai nghe", "tivi",
        "may hut bui", "may giat", "tu lanh", "dieu hoa", "noi com dien"
    }
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
    """Chuẩn hóa text để so sánh."""
    if not text:
        return ""
    # Chuyển về chữ thường và bỏ dấu
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        for item in soup.select('.product-item'):
            try:
                name = item.select_one('.product-name')
                price = item.select_one('.product-price')
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
                        'image_url': img['src'] if img and 'src' in img.attrs else None
                    }
                    products.append(product)
            except Exception as e:
                logger.error(f"Lỗi khi xử lý sản phẩm từ Điện Máy Xanh: {str(e)}")
                continue
                
        return products
    except Exception as e:
        logger.error(f"Lỗi khi crawl Điện Máy Xanh: {str(e)}")
        return []

def crawl_tgdd(query: str) -> List[Dict[str, Any]]:
    """Crawl dữ liệu từ Thế Giới Di Động."""
    try:
        url = f"https://www.thegioididong.com/tim-kiem?key={query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        for item in soup.select('.item'):
            try:
                name = item.select_one('h3')
                price = item.select_one('.price')
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
                        'image_url': img['src'] if img and 'src' in img.attrs else None
                    }
                    products.append(product)
            except Exception as e:
                logger.error(f"Lỗi khi xử lý sản phẩm từ TGDĐ: {str(e)}")
                continue
                
        return products
    except Exception as e:
        logger.error(f"Lỗi khi crawl TGDĐ: {str(e)}")
        return []

def run_crawler(crawler_func, product_name, source_name, collector):
    """Chạy crawler và thu thập kết quả."""
    try:
        logger.debug(f"Khởi chạy crawler {source_name} với từ khóa: {product_name}")
        results = crawler_func(product_name)
        
        # Xác định danh mục sản phẩm từ từ khóa tìm kiếm
        category = get_product_category(product_name)
        if category and results:
            # Lọc kết quả dựa trên danh mục
            filtered_results = []
            category_keywords = required_keywords[category]
            search_terms = normalize_text(product_name).split()
            
            for product in results:
                name = product["name"]
                relevance_score = 0
                
                # Kiểm tra từ khóa danh mục
                for keyword in category_keywords:
                    if text_contains(name, keyword):
                        relevance_score += 2
                        break  # Chỉ cần khớp một từ khóa danh mục
                
                # Kiểm tra từ khóa tìm kiếm
                for term in search_terms:
                    if text_contains(name, term):
                        relevance_score += 1
                
                # Chấp nhận sản phẩm nếu có ít nhất một từ khóa tìm kiếm khớp
                if relevance_score > 0:
                    filtered_results.append(product)
                    logger.debug(f"Chấp nhận sản phẩm (điểm={relevance_score}): {name}")
                else:
                    logger.debug(f"Loại bỏ sản phẩm không đủ phù hợp: {name}")
            
            # Thêm kết quả đã lọc vào collector
            if filtered_results:
                collector.add_results(filtered_results)
                logger.info(f"Crawler {source_name} hoàn thành, thu thập được {len(filtered_results)} sản phẩm phù hợp")
            else:
                logger.info(f"Crawler {source_name} không tìm thấy sản phẩm phù hợp với danh mục {category}")
        else:
            # Nếu không xác định được danh mục hoặc không có kết quả, thêm tất cả
            if results:
                collector.add_results(results)
                logger.info(f"Crawler {source_name} hoàn thành, thu thập được {len(results)} sản phẩm")
            else:
                logger.info(f"Crawler {source_name} không tìm thấy kết quả nào")
            
    except Exception as e:
        logger.error(f"Lỗi khi chạy crawler {source_name}: {str(e)}")

def get_product_category(query):
    """Xác định danh mục sản phẩm dựa trên query."""
    normalized_query = normalize_text(query).lower()
    max_matches = 0
    best_category = None

    for category, keywords in required_keywords.items():
        matches = sum(1 for keyword in keywords if keyword in normalized_query)
        if matches > max_matches:
            max_matches = matches
            best_category = category

    return best_category

def should_crawl_store(store_id, category):
    """Kiểm tra xem có nên crawl store này cho danh mục sản phẩm không."""
    if category is None:
        return True  # Nếu không xác định được danh mục, crawl tất cả
    return category in store_categories.get(store_id, set())

def search_official_stores(product_name, collector):
    """Tìm kiếm trên Điện Máy Xanh và Thế Giới Di Động."""
    category = get_product_category(product_name)
    logger.info(f"Danh mục sản phẩm xác định được: {category}")

    crawlers = []
    if should_crawl_store(1, category):  # Điện Máy Xanh
        crawlers.append((crawl_dienmayanh, "Điện Máy Xanh"))
        logger.info("Thêm crawler Điện Máy Xanh")
    
    if should_crawl_store(2, category):  # Thế Giới Di Động
        crawlers.append((crawl_tgdd, "Thế Giới Di Động"))
        logger.info("Thêm crawler Thế Giới Di Động")

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
    """Tìm kiếm trên Chợ Tốt với xử lý riêng."""
    category = get_product_category(product_name)
    
    if not should_crawl_store(3, category):
        logger.info(f"Bỏ qua crawl Chợ Tốt cho danh mục: {category}")
        return

    try:
        logger.info("Bắt đầu tìm kiếm trên Chợ Tốt")
        results = crawl_chotot(product_name)
        if results:
            collector.add_results(results)
        logger.info(f"Hoàn thành tìm kiếm trên Chợ Tốt, thu được {len(results)} kết quả")
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm trên Chợ Tốt: {str(e)}")

def search_in_database(query, min_price=None, max_price=None):
    """Tìm kiếm sản phẩm trong database với điều kiện giá."""
    try:
        normalized_query = normalize_text(query)
        search_terms = normalized_query.split()
        category = get_product_category(query)
        
        with get_db_cursor() as cursor:
            sql = """
                SELECT p.*, s.name as store_name
                FROM Products p
                JOIN Stores s ON p.store_id = s.id
                WHERE 1=1
            """
            params = []

            # Thêm điều kiện tìm kiếm cho từ khóa
            if search_terms:
                sql += " AND ("
                conditions = []
                for term in search_terms:
                    conditions.append("LOWER(p.name) LIKE ?")
                    params.append(f"%{term}%")
                sql += " OR ".join(conditions) + ")"

            # Thêm điều kiện giá
            if min_price is not None:
                sql += " AND p.price >= ?"
                params.append(min_price)
            if max_price is not None:
                sql += " AND p.price <= ?"
                params.append(max_price)

            cursor.execute(sql, params)
            columns = [column[0] for column in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                product = dict(zip(columns, row))
                name = product['name']
                
                # Tính điểm phù hợp
                relevance_score = 0
                
                # Điểm cho từ khóa tìm kiếm
                for term in search_terms:
                    if text_contains(name, term):
                        relevance_score += 1
                
                # Điểm cho danh mục
                if category:
                    for keyword in required_keywords[category]:
                        if text_contains(name, keyword):
                            relevance_score += 2
                            break
                
                if relevance_score > 0:
                    product['match_score'] = relevance_score
                    results.append(product)

            # Sắp xếp kết quả theo điểm phù hợp và giá
            results.sort(key=lambda x: (-x['match_score'], x['price']))
            
            # Xóa trường match_score trước khi trả về
            for product in results:
                del product['match_score']

            return {
                "query": query,
                "total": len(results),
                "results": results
            }
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm trong database: {str(e)}")
        return {"query": query, "total": 0, "results": []}

def search_product(product_name):
    try:
        logger.info(f"Bắt đầu tìm kiếm sản phẩm: {product_name}")
        init_db()

        collector = ResultCollector()
        standardized_query = normalize_text(product_name)

        # Chạy tìm kiếm song song cho các cửa hàng chính thức
        official_thread = threading.Thread(
            target=search_official_stores,
            args=(product_name, collector)
        )
        official_thread.start()

        # Chạy tìm kiếm Chợ Tốt riêng
        chotot_thread = threading.Thread(
            target=search_chotot,
            args=(product_name, collector)
        )
        chotot_thread.start()

        # Đợi cả hai hoàn thành
        official_thread.join()
        chotot_thread.join()
        logger.info("Tất cả các crawler đã hoàn thành")

        all_results = collector.get_results()
        logger.info(f"Tổng số kết quả thu thập được: {len(all_results)}")

        # Log số lượng sản phẩm theo từng store
        store_counts = {}
        for product in all_results:
            store_id = product.get("store_id")
            store_counts[store_id] = store_counts.get(store_id, 0) + 1
        logger.info(f"Số lượng sản phẩm theo store: {store_counts}")

        # Lọc sản phẩm
        filtered_results = []
        excluded_keywords = [
            'ốp lưng', 'sạc', 'cáp', 'kẹp', 'giá đỡ', 'bao da', 'miếng dán', 'pin dự phòng',
            'tai nghe', 'pin', 'kính', 'dán', 'gậy', 'tủ', 'phụ kiện', 'case', 'bộ sạc', 
            'dock', 'adapter', 'củ sạc', 'thẻ nhớ', 'điện thoại', 'smartphone', 'galaxy',
            'máy tính', 'laptop', 'tablet', 'ipad', 'watch', 'đồng hồ'
        ]

        # Xác định từ khóa chính dựa trên product_name
        product_name_lower = standardized_query.lower()
        matched_category = None
        for category, keywords in required_keywords.items():
            if any(keyword in product_name_lower for keyword in keywords):
                matched_category = category
                logger.info(f"Tìm thấy danh mục phù hợp: {category}")
                break

        for product in all_results:
            name_lower = normalize_text(product["name"]).lower()
            store_id = product.get("store_id")
            
            # Kiểm tra từ khóa loại trừ cho tất cả các store
            if any(keyword in name_lower for keyword in excluded_keywords):
                logger.debug(f"Sản phẩm bị lọc do chứa từ khóa loại trừ: {product['name']}")
                continue

            # Kiểm tra từ khóa bắt buộc cho tất cả các store
            if matched_category:
                category_keywords = required_keywords[matched_category]
                if not any(keyword in name_lower for keyword in category_keywords):
                    logger.debug(f"Sản phẩm bị lọc do thiếu từ khóa bắt buộc: {product['name']}")
                    continue
                else:
                    logger.debug(f"Sản phẩm phù hợp với từ khóa bắt buộc: {product['name']}")
            
            filtered_results.append(product)
            logger.debug(f"Giữ sản phẩm: {product['name']} - Store ID: {store_id}")

        logger.info(f"Số kết quả sau khi lọc: {len(filtered_results)}")
        
        # Log số lượng sản phẩm đã lọc theo từng store
        filtered_store_counts = {}
        for product in filtered_results:
            store_id = product.get("store_id")
            filtered_store_counts[store_id] = filtered_store_counts.get(store_id, 0) + 1
        logger.info(f"Số lượng sản phẩm sau khi lọc theo store: {filtered_store_counts}")

        # Sắp xếp ưu tiên Điện Máy Xanh và Thế Giới Di Động
        filtered_results.sort(key=lambda x: (x["store_id"] not in [1, 2], float(x["price"])))
        logger.info("Đã sắp xếp kết quả theo store và giá")

        try:
            save_products(filtered_results, product_name)
            logger.info(f"Đã lưu {len(filtered_results)} sản phẩm vào database")
        except Exception as e:
            logger.error(f"Lỗi khi lưu sản phẩm vào database: {str(e)}")

        return {
            "query": product_name,
            "total": len(filtered_results),
            "results": filtered_results[:50]
        }

    except Exception as e:
        logger.error(f"Lỗi trong search_product: {str(e)}")
        return {
            "query": product_name,
            "total": 0,
            "results": []
        }