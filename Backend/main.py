from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from Services.search import search_product, search_in_database
from Services.filter import filter_products, filter_products_by_price, search_local_products, compare_products
from Database.db import init_db, get_db_cursor, clear_history
import logging
import os
from typing import List, Optional, Dict, Any
import json

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả origins trong môi trường development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phục vụ các file tĩnh
app.mount("/static", StaticFiles(directory="Frontend"), name="static")

# Khởi tạo database khi khởi động
@app.on_event("startup")
async def startup_event():
    init_db()

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
async def search(product_name: str = Query(..., description="Tên sản phẩm cần tìm")):
    """
    Tìm kiếm sản phẩm từ các nguồn và lưu vào database
    """
    try:
        logger.info(f"Bắt đầu tìm kiếm: {product_name}")
        result = search_product(product_name)
        logger.info(f"Tìm kiếm '{product_name}' trả về {result['total']} kết quả")
        return result
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search-local")
async def search_local(query: str = Query(..., description="Từ khóa tìm kiếm")):
    """
    Tìm kiếm sản phẩm trong database local
    """
    try:
        logger.info(f"Tìm kiếm local: {query}")
        result = search_in_database(query)
        logger.info(f"Tìm kiếm local '{query}' trả về {result['total']} kết quả")
        return result
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm local: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/filter")
async def filter_results(
    query: str = Query(..., description="Từ khóa tìm kiếm"),
    min_price: Optional[float] = Query(None, description="Giá tối thiểu"),
    max_price: Optional[float] = Query(None, description="Giá tối đa")
):
    """
    Lọc kết quả tìm kiếm theo khoảng giá
    """
    try:
        logger.info(f"Lọc sản phẩm với giá từ {min_price} đến {max_price}")
        result = filter_products(query, min_price, max_price)
        logger.info(f"Lọc trả về {len(result)} kết quả")
        return result
    except Exception as e:
        logger.error(f"Lỗi khi lọc kết quả: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/products")
async def get_products(sort: Optional[str] = None):
    """
    Lấy danh sách tất cả sản phẩm
    """
    try:
        with get_db_cursor() as cursor:
            sql = """
                SELECT p.*, s.name as store_name
                FROM Products p
                JOIN Stores s ON p.store_id = s.id
            """
            
            if sort == "price_asc":
                sql += " ORDER BY p.price ASC"
            elif sort == "price_desc":
                sql += " ORDER BY p.price DESC"
            elif sort == "name":
                sql += " ORDER BY p.name"
            
            cursor.execute(sql)
            columns = [column[0] for column in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách sản phẩm: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# API endpoints cho tính năng yêu thích
@app.get("/api/favorites")
async def get_favorites():
    """
    Lấy danh sách sản phẩm yêu thích
    """
    try:
        with get_db_cursor() as cursor:
            sql = """
                SELECT p.*, s.name as store_name
                FROM Products p
                JOIN Stores s ON p.store_id = s.id
                WHERE p.is_favorite = 1
            """
            cursor.execute(sql)
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
            sql = "UPDATE Products SET is_favorite = 1 WHERE id = ?"
            cursor.execute(sql, (product_id,))
            cursor.commit()
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
            sql = "UPDATE Products SET is_favorite = 0 WHERE id = ?"
            cursor.execute(sql, (product_id,))
            cursor.commit()
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
            sql = "UPDATE Products SET is_favorite = 0"
            cursor.execute(sql)
            cursor.commit()
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
    try:
        clear_history()
        logger.info("Đã xóa lịch sử tìm kiếm thành công")
        return {"message": "Đã xóa lịch sử thành công"}
    except Exception as e:
        logger.error(f"Lỗi khi xóa lịch sử: {str(e)}")
        return {"error": "Có lỗi xảy ra khi xóa lịch sử"}, 500

@app.get("/favicon.ico")
async def favicon():
    try:
        return FileResponse("Frontend/favicon.ico")
    except FileNotFoundError:
        return Response(status_code=204)

if __name__ == "__main__":
    logger.info("Khởi động server FastAPI tại 127.0.0.1:8000")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)