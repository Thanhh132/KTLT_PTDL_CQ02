import requests
from bs4 import BeautifulSoup
from Crawler.utils import standardize_product_name

def crawl_thegioididong(product_name):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    url = f"https://www.thegioididong.com/tim-kiem?key={product_name.replace(' ', '+')}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        products = []
        items = soup.select("li.item")[:5]  # Giới hạn 5 sản phẩm
        for item in items:
            name_elem = item.select_one("h3")
            price_elem = item.select_one("strong")
            rating_elem = item.select_one("div.ratingresult span")
            link_elem = item.select_one("a")
            if name_elem and price_elem and link_elem:
                name = standardize_product_name(name_elem.text)
                price = price_elem.text.replace("₫", "").replace(".", "").strip()
                price = float(price)  # Chuyển thành float
                rating = float(rating_elem.text.split()[0]) if rating_elem else 0.0
                link = "https://www.thegioididong.com" + link_elem["href"]
                products.append({
                    "name": name,
                    "store_id": 3,  # ID của Thế Giới Di Động trong Stores
                    "price": price,
                    "rating": rating,
                    "link": link,
                    "category_id": None,
                    "updated_at": None
                })
        return products
    except Exception as e:
        print(f"Lỗi khi crawl Thế Giới Di Động: {e}")
        return []