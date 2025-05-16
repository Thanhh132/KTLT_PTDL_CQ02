import logging
from Database.db import get_db_cursor
from Services.search import normalize_text, text_contains

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def filter_products(query: str, min_price: float = None, max_price: float = None):
    """
    Lọc sản phẩm theo từ khóa và khoảng giá
    """
    try:
        with get_db_cursor() as cursor:
            # Xây dựng câu truy vấn SQL cơ bản
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

            # Thực thi truy vấn
            cursor.execute(sql, params)
            
            # Chuyển kết quả thành list of dict
            columns = [column[0] for column in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                product = dict(zip(columns, row))
                # Kiểm tra độ phù hợp của sản phẩm với từ khóa
                if query:
                    name = product['name']
                    relevance_score = 0
                    for term in search_terms:
                        if text_contains(name, term):
                            relevance_score += 1
                    if relevance_score > 0:
                        product['relevance_score'] = relevance_score
                        results.append(product)
                else:
                    results.append(product)

            # Sắp xếp kết quả theo độ phù hợp (nếu có tìm kiếm) và giá
            if query:
                results.sort(key=lambda x: (-x.get('relevance_score', 0), x['price']))
                # Xóa trường relevance_score
                for product in results:
                    if 'relevance_score' in product:
                        del product['relevance_score']
            else:
                results.sort(key=lambda x: x['price'])

            return results

    except Exception as e:
        logger.error(f"Lỗi khi lọc sản phẩm: {str(e)}")
        return []

def filter_products_by_price(min_price: float = None, max_price: float = None):
    """
    Lọc sản phẩm theo khoảng giá
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

            if min_price is not None:
                sql += " AND p.price >= ?"
                params.append(min_price)
            if max_price is not None:
                sql += " AND p.price <= ?"
                params.append(max_price)

            sql += " ORDER BY p.price ASC"
            cursor.execute(sql, params)
            
            columns = [column[0] for column in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return {
                "total": len(results),
                "results": results
            }

    except Exception as e:
        logger.error(f"Lỗi khi lọc theo giá: {str(e)}")
        return {"total": 0, "results": []}

def search_local_products(query: str):
    """
    Tìm kiếm sản phẩm trong database local
    """
    try:
        with get_db_cursor() as cursor:
            normalized_query = normalize_text(query).lower()
            search_terms = normalized_query.split()
            
            sql = """
                SELECT p.*, s.name as store_name
                FROM Products p
                JOIN Stores s ON p.store_id = s.id
                WHERE 1=1
            """
            params = []

            if search_terms:
                sql += " AND ("
                conditions = []
                for term in search_terms:
                    conditions.append("LOWER(p.name) LIKE ?")
                    params.append(f"%{term}%")
                sql += " OR ".join(conditions) + ")"

            cursor.execute(sql, params)
            columns = [column[0] for column in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                product = dict(zip(columns, row))
                name = product['name']
                relevance_score = 0
                
                for term in search_terms:
                    if text_contains(name, term):
                        relevance_score += 1
                
                if relevance_score > 0:
                    product['relevance_score'] = relevance_score
                    results.append(product)

            # Sắp xếp theo độ phù hợp và giá
            results.sort(key=lambda x: (-x['relevance_score'], x['price']))
            
            # Xóa trường relevance_score
            for product in results:
                del product['relevance_score']

            return {
                "query": query,
                "total": len(results),
                "results": results
            }

    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm local: {str(e)}")
        return {"query": query, "total": 0, "results": []}

def compare_products(product_ids: list):
    """
    So sánh các sản phẩm theo ID
    """
    try:
        with get_db_cursor() as cursor:
            # Lấy thông tin các sản phẩm
            placeholders = ','.join('?' * len(product_ids))
            sql = f"""
                SELECT p.*, s.name as store_name
                FROM Products p
                JOIN Stores s ON p.store_id = s.id
                WHERE p.id IN ({placeholders})
            """
            cursor.execute(sql, product_ids)
            
            columns = [column[0] for column in cursor.description]
            products = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            if not products:
                return {"error": "Không tìm thấy sản phẩm để so sánh"}

            # Tìm giá thấp nhất và cao nhất
            prices = [p['price'] for p in products]
            min_price = min(prices)
            max_price = max(prices)
            
            # Thêm thông tin so sánh vào mỗi sản phẩm
            for product in products:
                product['is_cheapest'] = product['price'] == min_price
                product['is_most_expensive'] = product['price'] == max_price
                product['price_diff_from_min'] = product['price'] - min_price
                product['price_diff_percentage'] = (
                    ((product['price'] - min_price) / min_price * 100)
                    if min_price > 0 else 0
                )

            return {
                "total": len(products),
                "products": products,
                "price_range": {
                    "min": min_price,
                    "max": max_price,
                    "diff": max_price - min_price
                }
            }

    except Exception as e:
        logger.error(f"Lỗi khi so sánh sản phẩm: {str(e)}")
        return {"error": str(e)} 