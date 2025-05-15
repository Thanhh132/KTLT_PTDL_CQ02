from Crawler.shopee import crawl_shopee
from Crawler.dienmayxanh import crawl_dienmayxanh
from Crawler.thegioididong import crawl_thegioididong
from Crawler.cellphones import crawl_cellphones
from Database.db import get_db_connection, init_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_product(product_name):
    try:
        logger.info(f"Bắt đầu tìm kiếm sản phẩm: {product_name}")
        init_db()  # Khởi tạo database và bảng
        
        results = []
        shopee_results = crawl_shopee(product_name)
        if shopee_results:
            results.extend(shopee_results)
            logger.info(f"Crawl Shopee: {len(shopee_results)} sản phẩm")
        else:
            logger.warning("Không crawl được dữ liệu từ Shopee")

        dienmayxanh_results = crawl_dienmayxanh(product_name)
        if dienmayxanh_results:
            results.extend(dienmayxanh_results)
            logger.info(f"Crawl Điện Máy Xanh: {len(dienmayxanh_results)} sản phẩm")
        else:
            logger.warning("Không crawl được dữ liệu từ Điện Máy Xanh")

        thegioididong_results = crawl_thegioididong(product_name)
        if thegioididong_results:
            results.extend(thegioididong_results)
            logger.info(f"Crawl Thế Giới Di Động: {len(thegioididong_results)} sản phẩm")
        else:
            logger.warning("Không crawl được dữ liệu từ Thế Giới Di Động")

        cellphones_results = crawl_cellphones(product_name)
        if cellphones_results:
            results.extend(cellphones_results)
            logger.info(f"Crawl Cellphones: {len(cellphones_results)} sản phẩm")
        else:
            logger.warning("Không crawl được dữ liệu từ Cellphones")

        # Lưu kết quả vào database
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            for result in results:
                cursor.execute("""
                    INSERT INTO Products (name, store_id, price, rating, link)
                    VALUES (?, ?, ?, ?, ?)
                """, (result['name'], result['store_id'], float(result['price']), result['rating'], result['link']))
            conn.commit()
            conn.close()
            logger.info(f"Lưu {len(results)} sản phẩm vào database")
        else:
            logger.error("Kết nối database thất bại")

        return results

    except Exception as e:
        logger.error(f"Lỗi trong search_product: {str(e)}")
        return []