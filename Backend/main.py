from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from Services.search import search_product
import logging
import uvicorn

app = FastAPI()
templates = Jinja2Templates(directory="Frontend")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchRequest(BaseModel):
    product_name: str

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    logger.info("Truy cập trang chủ")
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search")
async def search(request: SearchRequest):
    try:
        logger.info(f"Bắt đầu tìm kiếm: {request.product_name}")
        results = search_product(request.product_name)
        logger.info(f"Tìm kiếm '{request.product_name}' trả về {len(results)} kết quả")
        return {"results": results}
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm '{request.product_name}': {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    logger.info("Khởi động server FastAPI")
    uvicorn.run(app, host="127.0.0.1", port=8000)