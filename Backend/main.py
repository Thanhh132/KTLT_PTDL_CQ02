from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from Services.search import search_product
from Database.db import clear_history
import logging
import os

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

@app.get("/api/search")
async def search_endpoint(product_name: str = ""):
    if not product_name:
        return {"error": "Vui lòng cung cấp product_name"}
    logger.info(f"Bắt đầu tìm kiếm: {product_name}")
    result = search_product(product_name)
    logger.info(f"Tìm kiếm '{product_name}' trả về {len(result.get('results', []))} kết quả")
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

@app.get("/")
async def root():
    return FileResponse("Frontend/index.html")

# Mount thư mục Frontend để phục vụ các file tĩnh
app.mount("/static", StaticFiles(directory="Frontend"), name="frontend")

if __name__ == "__main__":
    logger.info("Khởi động server FastAPI tại 127.0.0.1:8000")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)