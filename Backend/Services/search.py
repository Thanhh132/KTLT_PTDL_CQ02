import threading
import logging
import re
from Database.db import init_db, save_products
from Crawler.dienmayxanh import crawl_dienmayxanh
from Crawler.thegioididong import crawl_thegioididong
from Crawler.chotot import crawl_chotot

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ResultCollector:
    def __init__(self):
        self.results = []
        self.lock = threading.Lock()

    def add_results(self, results):
        with self.lock:
            self.results.extend(results)

    def get_results(self):
        return self.results

def standardize_product_name(name):
    """Chuẩn hóa tên sản phẩm."""
    if not name:
        return ""
    name = re.sub(r'\s+', ' ', name.strip())
    name = re.sub(r'[^\w\s-]', '', name)
    return name

def run_crawler(crawler_func, product_name, source_name, collector):
    """Chạy crawler và thu thập kết quả."""
    try:
        logger.debug(f"Khởi chạy crawler {source_name} với từ khóa: {product_name}")
        results = crawler_func(product_name)
        collector.add_results(results)
        logger.debug(f"Crawler {source_name} hoàn thành, thu thập được {len(results)} sản phẩm")
    except Exception as e:
        logger.error(f"Lỗi khi chạy crawler {source_name}: {str(e)}")

def search_official_stores(product_name, collector):
    """Tìm kiếm trên Điện Máy Xanh và Thế Giới Di Động."""
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
    """Tìm kiếm trên Chợ Tốt với xử lý riêng."""
    try:
        logger.info("Bắt đầu tìm kiếm trên Chợ Tốt")
        results = crawl_chotot(product_name)
        if results:
            collector.add_results(results)
        logger.info(f"Hoàn thành tìm kiếm trên Chợ Tốt, thu được {len(results)} kết quả")
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm trên Chợ Tốt: {str(e)}")

def search_product(product_name):
    try:
        logger.info(f"Bắt đầu tìm kiếm sản phẩm: {product_name}")
        init_db()

        collector = ResultCollector()
        standardized_query = standardize_product_name(product_name)

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

        # Lọc sản phẩm
        filtered_results = []
        excluded_keywords = [
            'ốp lưng', 'sạc', 'cáp', 'kẹp', 'giá đỡ', 'bao da', 'miếng dán', 'pin dự phòng',
            'tai nghe', 'pin', 'kính', 'dán', 'gậy', 'tủ', 'phụ kiện', 'case', 'bộ sạc', 
            'dock', 'adapter', 'củ sạc', 'thẻ nhớ'
        ]
        required_keywords = {
            "dien thoai": ["dien thoai", "smartphone", "iphone", "samsung", "xiaomi", "oppo", "vivo"],
            "laptop": ["laptop", "macbook", "dell", "hp", "asus", "lenovo", "acer", "msi"],
            "may tinh bang": ["may tinh bang", "tablet", "ipad", "samsung tab"],
            "tai nghe": ["tai nghe", "headphone", "earphone", "airpods", "sony"],
            "tivi": ["tivi", "tv", "smart tv", "samsung tv", "lg tv"]
        }

        # Xác định từ khóa chính dựa trên product_name
        product_name_lower = standardized_query.lower()
        matched_category = None
        for category, keywords in required_keywords.items():
            if any(keyword in product_name_lower for keyword in keywords):
                matched_category = category
                break

        for product in all_results:
            name_lower = standardize_product_name(product["name"]).lower()
            
            # Chỉ áp dụng excluded_keywords cho Chợ Tốt
            if product["store_id"] == 3:
                if any(keyword in name_lower for keyword in excluded_keywords):
                    logger.debug(f"Sản phẩm Chợ Tốt bị lọc do chứa từ khóa loại trừ: {product['name']}")
                    continue
                # Kiểm tra từ khóa bắt buộc cho Chợ Tốt
                if matched_category:
                    category_keywords = required_keywords[matched_category]
                    if not any(keyword in name_lower for keyword in category_keywords):
                        logger.debug(f"Sản phẩm Chợ Tốt bị lọc do thiếu từ khóa bắt buộc: {product['name']}")
                        continue
            
            filtered_results.append(product)
            logger.debug(f"Giữ sản phẩm: {product['name']} - Store ID: {product['store_id']}")

        logger.info(f"Số kết quả sau khi lọc: {len(filtered_results)}")

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