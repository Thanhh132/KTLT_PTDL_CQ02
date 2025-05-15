import requests
from bs4 import BeautifulSoup
from Crawler.utils import standardize_product_name

def crawl_shopee(product_name):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    url = f"https://shopee.vn/search?keyword={product_name.replace(' ', '%20')}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        products = []
        items = soup.select("div.shopee-search-item-result__item")[:5]
        for item in items:
            name_elem = item.select_one("div._10Wbs-")
            price_elem = item.select_one("span._2lG9TJ")
            rating_elem = item.select_one("div._3aG9TJ")
            link_elem = item.select_one("a")
            if name_elem and price_elem and link_elem:
                name = standardize_product_name(name_elem.text)
                price = price_elem.text.replace("₫", "").replace(".", "").strip()
                price = float(price)  # Chuyển thành float
                rating = float(rating_elem.text) if rating_elem else 0.0
                link = "https://shopee.vn" + link_elem["href"]
                products.append({
                    "name": name,
                    "store_id": 1,  # Shopee ID từ bảng Stores
                    "price": price,
                    "rating": rating,
                    "link": link,
                    "category_id": None,
                    "updated_at": None
                })
        return products
    except Exception as e:
        print(f"Lỗi khi crawl Shopee: {e}")
        return []