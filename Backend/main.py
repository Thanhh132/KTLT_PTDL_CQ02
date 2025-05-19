from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from Services.search import search_product, search_in_database, load_database_to_web
from Services.filter import filter_products, filter_products_by_price, search_local_products, compare_products
from Services.update_service import check_and_update_products
from Database.db import init_db, get_db_cursor, clear_history
from pydantic import BaseModel, Field
import logging
import os
from typing import List, Optional, Dict, Any
import json
from json import JSONDecodeError
from math import ceil
from functools import lru_cache
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for pagination and caching
MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 10
CACHE_TIMEOUT = 300  # 5 minutes in seconds

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page")
    
    def get_skip(self) -> int:
        return (self.page - 1) * self.page_size
    
    def get_limit(self) -> int:
        return self.page_size
    
    @staticmethod
    def get_pagination_info(total_items: int, params: 'PaginationParams') -> dict:
        total_pages = ceil(total_items / params.page_size)
        current_page = min(params.page, total_pages) if total_pages > 0 else 1
        
        return {
            "total": total_items,
            "page": current_page,
            "page_size": params.page_size,
            "total_pages": total_pages,
            "has_previous": current_page > 1,
            "has_next": current_page < total_pages,
            "previous_page": current_page - 1 if current_page > 1 else None,
            "next_page": current_page + 1 if current_page < total_pages else None
        }

class CachedResponse:
    def __init__(self, data: dict):
        self.data = data
        self.timestamp = datetime.now()

    def is_valid(self) -> bool:
        return (datetime.now() - self.timestamp).total_seconds() < CACHE_TIMEOUT

# Cache for pagination results
pagination_cache: Dict[str, CachedResponse] = {}

def get_cache_key(product_name: str, pagination: PaginationParams, sort: Optional[str], min_price: Optional[float], max_price: Optional[float]) -> str:
    return f"{product_name}:{pagination.page}:{pagination.page_size}:{sort}:{min_price}:{max_price}"

def get_cached_response(cache_key: str) -> Optional[dict]:
    if cache_key in pagination_cache:
        cached = pagination_cache[cache_key]
        if cached.is_valid():
            return cached.data
        del pagination_cache[cache_key]
    return None

def set_cached_response(cache_key: str, response: dict):
    pagination_cache[cache_key] = CachedResponse(response)
    # Cleanup old cache entries
    current_time = datetime.now()
    expired_keys = [k for k, v in pagination_cache.items() 
                   if (current_time - v.timestamp).total_seconds() >= CACHE_TIMEOUT]
    for k in expired_keys:
        del pagination_cache[k]

app = FastAPI()

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả origins trong môi trường development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phục vụ các file tĩnh với cache control
app.mount("/css", StaticFiles(directory="Frontend/CSS"), name="css")
app.mount("/js", StaticFiles(directory="Frontend/JS"), name="js")

# Khởi tạo database khi khởi động
@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Đã khởi động ứng dụng")

@app.get("/")
async def root():
    return FileResponse("Frontend/index.html")

@app.get("/favorites")
async def favorites():
    return FileResponse("Frontend/favorites.html")

@app.get("/favorites.html")
async def favorites_html():
    return FileResponse("Frontend/favorites.html")

@app.get("/api")
async def api_root():
    return {"message": "Welcome to Price Comparison API"}

@app.post("/api/search")
async def search(
    product_name: str = Query(..., description="Tên sản phẩm cần tìm"),
    pagination: PaginationParams = None,
    sort: Optional[str] = Query(None, description="Cách sắp xếp (price_asc, price_desc, name)"),
    min_price: Optional[float] = Query(None, description="Giá tối thiểu"),
    max_price: Optional[float] = Query(None, description="Giá tối đa")
):
    """
    Tìm kiếm sản phẩm từ các nguồn và lưu vào database với phân trang
    """
    try:
        # Chuẩn hóa từ khóa tìm kiếm
        normalized_query = normalize_search_query(product_name)
        logger.info(f"Tìm kiếm với từ khóa chuẩn hóa: {normalized_query}")

        # Tìm kiếm sản phẩm
        result = search_product(normalized_query)
        products = result.get("results", [])
        
        # Lọc theo khoảng giá nếu có
        if min_price is not None or max_price is not None:
            products = [p for p in products if (
                (min_price is None or p["price"] >= min_price) and
                (max_price is None or p["price"] <= max_price)
            )]
        
        # Sắp xếp sản phẩm nếu có yêu cầu
        if sort == "price_asc":
            products.sort(key=lambda x: x["price"])
        elif sort == "price_desc":
            products.sort(key=lambda x: x["price"], reverse=True)
        elif sort == "name":
            products.sort(key=lambda x: x["name"])
        
        # Tính toán phân trang
        total = len(products)
        pagination_info = PaginationParams.get_pagination_info(total, pagination)
        
        # Lấy sản phẩm cho trang hiện tại
        start_idx = pagination.get_skip()
        end_idx = start_idx + pagination.get_limit()
        current_page_products = products[start_idx:end_idx]
        
        # Tạo response
        response = {
            **pagination_info,
            "results": current_page_products,
            "query": product_name
        }

        return response
        
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm: {str(e)}")
        return {
            "total": 0,
            "page": pagination.page if pagination else 1,
            "page_size": pagination.page_size if pagination else DEFAULT_PAGE_SIZE,
            "total_pages": 0,
            "results": [],
            "query": product_name
        }

def normalize_search_query(query: str) -> str:
    """
    Chuẩn hóa từ khóa tìm kiếm:
    - Chuyển về chữ thường
    - Bỏ dấu tiếng Việt
    - Thay thế các ký tự đặc biệt bằng khoảng trắng
    - Chuẩn hóa khoảng trắng
    """
    import re
    from unidecode import unidecode

    # Chuyển về chữ thường và bỏ dấu
    normalized = unidecode(query.lower())
    
    # Thay thế các ký tự đặc biệt bằng khoảng trắng
    normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
    
    # Chuẩn hóa khoảng trắng
    normalized = ' '.join(normalized.split())
    
    return normalized

@app.get("/api/search-local")
async def search_local(
    query: str = Query(..., description="Từ khóa tìm kiếm"),
    page: int = Query(1, description="Số trang"),
    page_size: int = Query(0, description="Số sản phẩm mỗi trang (0 để lấy tất cả)"),
    sort: Optional[str] = Query(None, description="Cách sắp xếp (price_asc, price_desc, name)"),
    min_price: Optional[float] = Query(None, description="Giá tối thiểu"),
    max_price: Optional[float] = Query(None, description="Giá tối đa")
):
    """
    Tìm kiếm sản phẩm trong database local với phân trang
    """
    try:
        # Chuẩn hóa từ khóa tìm kiếm
        normalized_query = normalize_search_query(query)
        logger.info(f"Tìm kiếm local với từ khóa chuẩn hóa: {normalized_query}")

        # Xây dựng câu truy vấn SQL
        sql = """
            SELECT p.*, s.name as store_name
            FROM Products p
            JOIN Stores s ON p.store_id = s.id
            WHERE 1=1
        """
        params = []

        # Thêm điều kiện tìm kiếm
        sql += """
            AND (
                LOWER(p.name) LIKE ? 
                OR ? LIKE CONCAT('%', LOWER(p.name), '%')
            )
        """
        search_pattern = f"%{normalized_query}%"
        params.extend([search_pattern, normalized_query])

        # Thêm điều kiện lọc giá
        if min_price is not None:
            sql += " AND p.price >= ?"
            params.append(min_price)
        if max_price is not None:
            sql += " AND p.price <= ?"
            params.append(max_price)

        # Thêm điều kiện sắp xếp
        if sort == "price_asc":
            sql += " ORDER BY p.price ASC"
        elif sort == "price_desc":
            sql += " ORDER BY p.price DESC"
        elif sort == "name":
            sql += " ORDER BY p.name"
        else:
            sql += " ORDER BY p.last_updated DESC"

        # Thực thi truy vấn
        with get_db_cursor() as cursor:
            cursor.execute(sql, params)
            columns = [column[0] for column in cursor.description]
            all_products = [dict(zip(columns, row)) for row in cursor.fetchall()]

            total = len(all_products)

            # Xử lý phân trang
            if page_size > 0:
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                current_page_products = all_products[start_idx:end_idx]
            else:
                current_page_products = all_products
                page_size = total
                page = 1

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 1,
                "results": current_page_products,
                "query": query
            }

    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm local: {str(e)}")
        return {
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "results": [],
            "query": query,
            "error": str(e)
        }

@app.get("/api/filter")
async def filter_results(
    query: Optional[str] = Query(None, description="Từ khóa tìm kiếm"),
    min_price: Optional[float] = Query(None, description="Giá tối thiểu"),
    max_price: Optional[float] = Query(None, description="Giá tối đa"),
    sort: Optional[str] = Query(None, description="Cách sắp xếp (price_asc, price_desc)"),
    condition: Optional[str] = Query(None, description="Lọc theo độ mới (new_to_old, old_to_new)")
):
    """
    Lọc kết quả tìm kiếm theo khoảng giá, sắp xếp và độ mới
    """
    try:
        result = filter_products(query, min_price, max_price, sort, condition)
        return {"results": result}
    except Exception as e:
        logger.error(f"Lỗi khi lọc sản phẩm: {str(e)}")
        return {"results": []}

@app.get("/api/products")
async def get_products(
    page: int = Query(1, description="Số trang hiện tại"),
    page_size: int = Query(20, description="Số sản phẩm mỗi trang"),
    min_price: Optional[float] = Query(None, description="Giá tối thiểu"),
    max_price: Optional[float] = Query(None, description="Giá tối đa"),
    sort: Optional[str] = Query(None, description="Cách sắp xếp (price_asc, price_desc)")
):
    """
    Lấy danh sách tất cả sản phẩm với phân trang, lọc giá và sắp xếp
    """
    try:
        logger.info("Bắt đầu lấy danh sách sản phẩm")
        logger.info(f"Tham số: page={page}, page_size={page_size}, min_price={min_price}, max_price={max_price}, sort={sort}")
        
        with get_db_cursor() as cursor:
            # Xây dựng câu truy vấn cơ bản
            base_query = """
                SELECT p.*, 
                       CASE s.id 
                           WHEN 1 THEN N'Điện Máy Xanh'
                           WHEN 2 THEN N'Thế Giới Di Động'
                           WHEN 3 THEN N'Chợ Tốt'
                           ELSE s.name 
                       END as store_name,
                       CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
                FROM Products p
                JOIN Stores s ON p.store_id = s.id
                LEFT JOIN Favorites f ON p.id = f.product_id AND f.user_id = 1
                WHERE 1=1
            """
            
            # Thêm điều kiện lọc giá
            params = []
            if min_price is not None:
                base_query += " AND p.price >= ?"
                params.append(min_price)
            if max_price is not None:
                base_query += " AND p.price <= ?"
                params.append(max_price)
            
            # Đếm tổng số sản phẩm thỏa mãn điều kiện lọc giá
            count_query = f"SELECT COUNT(*) FROM ({base_query}) as filtered_products"
            cursor.execute(count_query, params)
            total_products = cursor.fetchone()[0]
            
            # Thêm sắp xếp
            if sort == "price_asc":
                base_query += " ORDER BY p.price ASC"
            elif sort == "price_desc":
                base_query += " ORDER BY p.price DESC"
            else:
                # Mặc định sắp xếp theo thời gian cập nhật nếu không có yêu cầu sắp xếp theo giá
                base_query += " ORDER BY p.last_updated DESC"
            
            # Thêm phân trang
            offset = (page - 1) * page_size
            base_query += " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
            params.extend([offset, page_size])
            
            # Thực thi truy vấn chính
            cursor.execute(base_query, params)
            columns = [column[0] for column in cursor.description]
            products = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            total_pages = ceil(total_products / page_size) if page_size > 0 else 1
            
            logger.info(f"Đã tải {len(products)} sản phẩm cho trang {page}/{total_pages}")
            
            return {
                "total": total_products,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "results": products,
                "stats": {
                    "total_products": total_products,
                    "min_price": min_price,
                    "max_price": max_price,
                    "sort": sort
                },
                "last_updated": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách sản phẩm: {str(e)}")
        return {
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "results": [],
            "stats": {"total_products": 0},
            "error": str(e)
        }

# API endpoints cho tính năng yêu thích
@app.get("/api/favorites")
async def get_favorites():
    """
    Lấy danh sách sản phẩm yêu thích
    """
    try:
        with get_db_cursor() as cursor:
            # Sử dụng user_id mặc định là 1
            default_user_id = 1
            sql = """
                SELECT p.*, 
                       CASE s.id 
                           WHEN 1 THEN N'Điện Máy Xanh'
                           WHEN 2 THEN N'Thế Giới Di Động'
                           WHEN 3 THEN N'Chợ Tốt'
                           ELSE s.name 
                       END as store_name,
                       1 as is_favorite
                FROM Products p
                JOIN Stores s ON p.store_id = s.id
                JOIN Favorites f ON p.id = f.product_id
                WHERE f.user_id = ?
            """
            cursor.execute(sql, (default_user_id,))
            columns = [column[0] for column in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách yêu thích: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/favorites/{product_id}")
async def add_to_favorites(product_id: int):
    """
    Thêm sản phẩm vào danh sách yêu thích
    """
    try:
        with get_db_cursor() as cursor:
            # Sử dụng user_id mặc định là 1
            default_user_id = 1
            
            # Kiểm tra xem sản phẩm đã tồn tại trong yêu thích chưa
            cursor.execute("SELECT id FROM Favorites WHERE product_id = ? AND user_id = ?", 
                         (product_id, default_user_id))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO Favorites (product_id, user_id) VALUES (?, ?)",
                    (product_id, default_user_id)
                )
            return {"message": "Đã thêm vào yêu thích"}
    except Exception as e:
        logger.error(f"Lỗi khi thêm vào yêu thích: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/favorites/{product_id}")
async def remove_from_favorites(product_id: int):
    """
    Xóa sản phẩm khỏi danh sách yêu thích
    """
    try:
        with get_db_cursor() as cursor:
            # Sử dụng user_id mặc định là 1
            default_user_id = 1
            cursor.execute(
                "DELETE FROM Favorites WHERE product_id = ? AND user_id = ?",
                (product_id, default_user_id)
            )
            return {"message": "Đã xóa khỏi yêu thích"}
    except Exception as e:
        logger.error(f"Lỗi khi xóa khỏi yêu thích: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/favorites")
async def clear_favorites():
    """
    Xóa tất cả sản phẩm khỏi danh sách yêu thích
    """
    try:
        with get_db_cursor() as cursor:
            # Sử dụng user_id mặc định là 1
            default_user_id = 1
            cursor.execute("DELETE FROM Favorites WHERE user_id = ?", (default_user_id,))
            return {"message": "Đã xóa tất cả yêu thích"}
    except Exception as e:
        logger.error(f"Lỗi khi xóa tất cả yêu thích: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compare")
async def compare_endpoint(product_ids: List[int]):
    """Endpoint để so sánh các sản phẩm."""
    if len(product_ids) < 2:
        return {"error": "Cần ít nhất 2 sản phẩm để so sánh"}
    logger.info(f"So sánh các sản phẩm: {product_ids}")
    result = compare_products(product_ids)
    logger.info(f"So sánh trả về {result.get('total', 0)} kết quả")
    return result

@app.post("/api/clear-history")
async def clear_history_endpoint():
    """
    Xóa lịch sử tìm kiếm, giá và sản phẩm, nhưng giữ lại các sản phẩm yêu thích
    """
    try:
        with get_db_cursor() as cursor:
            # Bắt đầu transaction
            cursor.execute("BEGIN TRANSACTION")
            try:
                # 1. Xóa Notifications (phụ thuộc vào Products)
                cursor.execute("""
                    IF OBJECT_ID('Notifications', 'U') IS NOT NULL
                        DELETE FROM Notifications 
                        WHERE product_id NOT IN (
                            SELECT DISTINCT product_id 
                            FROM Favorites
                        );
                """)
                
                # 2. Xóa PriceHistory (phụ thuộc vào Products)
                cursor.execute("""
                    IF OBJECT_ID('PriceHistory', 'U') IS NOT NULL
                        DELETE FROM PriceHistory 
                        WHERE product_id NOT IN (
                            SELECT DISTINCT product_id 
                            FROM Favorites
                        );
                """)
                
                # 3. Xóa SearchHistory (độc lập)
                cursor.execute("""
                    IF OBJECT_ID('SearchHistory', 'U') IS NOT NULL
                        DELETE FROM SearchHistory;
                """)
                
                # 4. Xóa Products nhưng giữ lại các sản phẩm trong Favorites
                cursor.execute("""
                    IF OBJECT_ID('Products', 'U') IS NOT NULL
                        DELETE FROM Products 
                        WHERE id NOT IN (
                            SELECT DISTINCT product_id 
                            FROM Favorites
                        );
                """)
                
                # Commit transaction
                cursor.execute("COMMIT")
                
                logger.info("Đã xóa lịch sử và dữ liệu sản phẩm thành công (giữ lại sản phẩm yêu thích)")
                return {"message": "Đã xóa lịch sử và dữ liệu sản phẩm thành công (giữ lại sản phẩm yêu thích)", "success": True}
            except Exception as e:
                # Rollback nếu có lỗi
                cursor.execute("ROLLBACK")
                logger.error(f"Lỗi khi xóa lịch sử và dữ liệu, thực hiện rollback: {str(e)}")
                raise
    except Exception as e:
        logger.error(f"Lỗi khi xóa lịch sử và dữ liệu: {str(e)}")
        return {"message": f"Lỗi khi xóa lịch sử và dữ liệu: {str(e)}", "success": False}

@app.get("/favicon.ico")
async def favicon():
    try:
        return FileResponse("Frontend/favicon.ico")
    except FileNotFoundError:
        return Response(status_code=204)

@app.get("/api/products/{product_id}/update-status")
async def get_product_update_status(product_id: int):
    """Kiểm tra trạng thái cập nhật của sản phẩm"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT name, price, last_updated,
                       DATEDIFF(hour, last_updated, GETDATE()) as hours_since_update
                FROM Products
                WHERE id = ?
            """, (product_id,))
            result = cursor.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
                
            columns = ['name', 'price', 'last_updated', 'hours_since_update']
            product_info = dict(zip(columns, result))
            
            # Thêm cảnh báo nếu quá 24h
            product_info['needs_update'] = product_info['hours_since_update'] >= 24
            product_info['warning_message'] = (
                "Thông tin sản phẩm có thể đã thay đổi do chưa được cập nhật trong 24h qua"
                if product_info['needs_update'] else None
            )
            
            return product_info
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái cập nhật: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/products/{product_id}/price-history")
async def get_price_history(product_id: int):
    """Lấy lịch sử giá của sản phẩm"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT p.name as product_name,
                       ph.price,
                       ph.recorded_at,
                       s.name as store_name
                FROM PriceHistory ph
                JOIN Products p ON ph.product_id = p.id
                JOIN Stores s ON p.store_id = s.id
                WHERE p.id = ?
                ORDER BY ph.recorded_at DESC
            """, (product_id,))
            
            columns = ['product_name', 'price', 'recorded_at', 'store_name']
            history = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Tính toán thay đổi giá
            for i in range(len(history)-1):
                current_price = float(history[i]['price'])
                previous_price = float(history[i+1]['price'])
                price_change = current_price - previous_price
                price_change_percent = (price_change / previous_price) * 100
                
                history[i]['price_change'] = price_change
                history[i]['price_change_percent'] = round(price_change_percent, 2)
            
            return {"history": history}
    except Exception as e:
        logger.error(f"Lỗi khi lấy lịch sử giá: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/outdated-products")
async def get_outdated_products():
    """Lấy danh sách sản phẩm chưa được cập nhật trong 24h"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.name, p.price, p.last_updated,
                       DATEDIFF(hour, p.last_updated, GETDATE()) as hours_since_update,
                       s.name as store_name
                FROM Products p
                JOIN Stores s ON p.store_id = s.id
                WHERE DATEDIFF(hour, p.last_updated, GETDATE()) >= 24
                ORDER BY p.last_updated ASC
            """)
            
            columns = ['id', 'name', 'price', 'last_updated', 'hours_since_update', 'store_name']
            products = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return {
                "total": len(products),
                "products": products
            }
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách sản phẩm cũ: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/notifications")
async def get_notifications(unread_only: bool = False):
    """Lấy danh sách thông báo thay đổi giá"""
    try:
        with get_db_cursor() as cursor:
            # Kiểm tra xem bảng Notifications có tồn tại không
            cursor.execute("""
                IF EXISTS (SELECT * FROM sys.tables WHERE name = 'Notifications')
                BEGIN
                    SELECT n.*, p.name as product_name, p.image_url
                    FROM Notifications n
                    JOIN Products p ON n.product_id = p.id
                    WHERE (? = 0 OR n.is_read = 0)
                    ORDER BY n.created_at DESC
                END
                ELSE
                BEGIN
                    SELECT 0 as total, 0 as unread_count
                END
            """, (0 if unread_only else 1,))
            
            if cursor.description:  # Nếu có kết quả trả về
                columns = [column[0] for column in cursor.description]
                notifications = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                return {
                    "total": len(notifications),
                    "unread_count": len([n for n in notifications if not n['is_read']]),
                    "notifications": notifications
                }
            else:
                return {
                    "total": 0,
                    "unread_count": 0,
                    "notifications": []
                }
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông báo: {str(e)}")
        return {
            "total": 0,
            "unread_count": 0,
            "notifications": [],
            "error": "Có lỗi xảy ra khi lấy thông báo"
        }

@app.post("/api/notifications/{notification_id}/mark-read")
async def mark_notification_read(notification_id: int):
    """Đánh dấu thông báo đã đọc"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE Notifications SET is_read = 1 WHERE id = ?",
                (notification_id,)
            )
            return {"message": "Đã đánh dấu đã đọc"}
    except Exception as e:
        logger.error(f"Lỗi khi đánh dấu đã đọc: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_endpoint(request: Request):
    """
    Endpoint tìm kiếm sản phẩm
    """
    try:
        # Đọc dữ liệu JSON từ body request
        data = await request.json()
        product_name = data.get("product_name")
        condition = data.get("condition")

        if not product_name:
            raise HTTPException(status_code=400, detail="Thiếu tên sản phẩm cần tìm")

        logger.info(f"Bắt đầu tìm kiếm: {product_name}, condition: {condition}")
        result = search_product(product_name, condition)
        
        # Đảm bảo format trả về đúng với yêu cầu của frontend
        response = {
            "total": result.get("total", 0),
            "results": result.get("results", []),
            "query": product_name
        }
        
        logger.info(f"Tìm kiếm '{product_name}' trả về {response['total']} kết quả")
        return response
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail="Dữ liệu không đúng định dạng JSON")
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm: {str(e)}")
        # Trả về kết quả rỗng khi có lỗi thay vì raise exception
        return {
            "total": 0,
            "results": [],
            "query": product_name if product_name else ""
        }

@app.get("/load-database")
async def load_database():
    """
    Load toàn bộ database lên web
    """
    try:
        result = load_database_to_web()
        return result
    except Exception as e:
        logger.error(f"Lỗi khi load database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Middleware để thêm cache control headers
@app.middleware("http")
async def add_cache_control_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/css/", "/js/")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

if __name__ == "__main__":
    logger.info("Khởi động server FastAPI tại 127.0.0.1:8000")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)