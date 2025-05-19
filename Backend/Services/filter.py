import logging
from Database.db import get_db_cursor
from Services.search import normalize_text, text_contains

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def filter_products(query: str, min_price: float = None, max_price: float = None):
    """
    Lọc sản phẩm theo từ khóa và khoảng giá với khả năng tìm kiếm nâng cao
    """
    try:
        with get_db_cursor() as cursor:
            # Xây dựng câu truy vấn SQL cơ bản
            sql = """
                SELECT p.*, s.name as store_name,
                       CASE WHEN ? IS NULL THEN 0 ELSE 1 END as has_query
                FROM Products p
                JOIN Stores s ON p.store_id = s.id
                WHERE 1=1
            """
            params = [query]

            # Thêm điều kiện tìm kiếm theo từ khóa
            if query:
                normalized_query = normalize_text(query)
                search_terms = normalized_query.split()
                
                if search_terms:
                    sql += " AND ("
                    term_conditions = []
                    
                    for term in search_terms:
                        # Tìm kiếm chính xác
                        exact_match = f"LOWER(p.name) LIKE ?"
                        params.append(f"%{term}%")
                        
                        # Tìm kiếm với dấu cách
                        space_match = f"LOWER(p.name) LIKE ?"
                        params.append(f"% {term} %")
                        
                        # Tìm kiếm đầu từ
                        start_match = f"LOWER(p.name) LIKE ?"
                        params.append(f"{term}%")
                        
                        term_conditions.append(f"({exact_match} OR {space_match} OR {start_match})")
                    
                    sql += " AND ".join(term_conditions) + ")"

            # Thêm điều kiện giá
            if min_price is not None:
                sql += " AND p.price >= ?"
                params.append(min_price)
            if max_price is not None:
                sql += " AND p.price <= ?"
                params.append(max_price)

            # Thêm ORDER BY để ưu tiên kết quả phù hợp nhất
            sql += """
                ORDER BY 
                    CASE 
                        WHEN has_query = 1 AND LOWER(p.name) LIKE ? THEN 1  -- Ưu tiên 1: Khớp chính xác
                        WHEN has_query = 1 AND LOWER(p.name) LIKE ? THEN 2  -- Ưu tiên 2: Chứa từ khóa
                        ELSE 3                                              -- Ưu tiên 3: Các kết quả khác
                    END,
                    p.price ASC
            """
            if query:
                params.extend([f"%{normalized_query}%", f"%{normalized_query}%"])
            else:
                params.extend([None, None])

            # Thực thi truy vấn
            cursor.execute(sql, params)
            
            # Chuyển kết quả thành list of dict
            columns = [column[0] for column in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                product = dict(zip(columns, row))
                if 'has_query' in product:
                    del product['has_query']
                results.append(product)

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
    Tìm kiếm sản phẩm trong database local với độ linh hoạt cao
    """
    try:
        with get_db_cursor() as cursor:
            # Chuẩn hóa query và tách từ khóa
            normalized_query = normalize_text(query).lower()
            # Chỉ lấy các từ có ý nghĩa (độ dài > 1)
            search_terms = [term for term in normalized_query.split() if len(term) > 1]
            
            if not search_terms:
                return {
                    "query": query,
                    "total": 0,
                    "results": []
                }
            
            sql = """
                SELECT p.*, s.name as store_name
                FROM Products p
                JOIN Stores s ON p.store_id = s.id
                WHERE 1=1
            """
            params = []

            # Xây dựng điều kiện tìm kiếm linh hoạt
            sql += " AND ("
            conditions = []
            
            # 1. Tìm kiếm từng từ riêng lẻ
            for term in search_terms:
                conditions.append("LOWER(p.name) LIKE ?")
                params.append(f"%{term}%")
            
            # 2. Tìm kiếm cả cụm từ
            if len(search_terms) > 1:
                full_query = ' '.join(search_terms)
                conditions.append("LOWER(p.name) LIKE ?")
                params.append(f"%{full_query}%")
            
            # 3. Tìm kiếm với dấu cách linh hoạt
            if len(search_terms) > 1:
                flexible_query = '%'.join(search_terms)
                conditions.append("LOWER(p.name) LIKE ?")
                params.append(f"%{flexible_query}%")
            
            sql += " OR ".join(conditions) + ")"

            cursor.execute(sql, params)
            columns = [column[0] for column in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                product = dict(zip(columns, row))
                name = product['name'].lower()
                relevance_score = 0
                
                # 1. Điểm cho từng từ khóa riêng lẻ
                for term in search_terms:
                    if term in name:
                        relevance_score += 1
                        # Bonus điểm nếu từ khóa ở đầu tên
                        if name.startswith(term):
                            relevance_score += 0.5
                        # Bonus điểm nếu khớp chính xác
                        if f" {term} " in f" {name} ":
                            relevance_score += 0.5
                
                # 2. Điểm cho cụm từ hoàn chỉnh
                if len(search_terms) > 1:
                    full_query = ' '.join(search_terms)
                    if full_query in name:
                        relevance_score += 2
                        if name.startswith(full_query):
                            relevance_score += 1
                
                # 3. Điểm cho store uy tín
                if product['store_id'] in [1, 2]:  # TGDD và DMX
                    relevance_score += 0.5
                
                # 4. Điểm cho tên ngắn gọn (ưu tiên tên không quá dài)
                if len(name.split()) <= 5:
                    relevance_score += 0.5
                
                # 5. Điểm cho khớp category
                category_id = get_product_category(name)
                search_category = get_product_category(query)
                if category_id and search_category and category_id == search_category:
                    relevance_score += 1
                
                # Thêm sản phẩm nếu có điểm phù hợp
                if relevance_score > 0:
                    product['relevance_score'] = relevance_score
                    results.append(product)

            # Sắp xếp theo độ phù hợp và giá
            results.sort(key=lambda x: (-x['relevance_score'], float(x['price'])))
            
            # Xóa điểm phù hợp trước khi trả về
            for product in results:
                del product['relevance_score']

            return {
                "query": query,
                "total": len(results),
                "results": results
            }
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm local: {str(e)}")
        return {
            "query": query,
            "total": 0,
            "results": []
        }

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