import re
import unicodedata

def standardize_product_name(text):
    """
    Chuẩn hóa tên sản phẩm:
    - Chuyển về chữ thường
    - Bỏ dấu
    - Bỏ khoảng trắng thừa
    - Bỏ ký tự đặc biệt
    """
    if not text:
        return ""
    
    text = text.lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r'[^\w\s]', ' ', text)
    text = ' '.join(text.split())
    
    return text

def get_category_id_from_keyword(keyword):
    """
    Lấy category_id từ từ khóa tìm kiếm
    """
    keyword = standardize_product_name(keyword)
    
    category_mapping = {
        1: {"keywords": ["dien thoai", "smartphone", "iphone", "samsung", "oppo", "xiaomi", "vivo"]},
        2: {"keywords": ["laptop", "may tinh xach tay", "macbook", "notebook"]},
        3: {"keywords": ["may tinh bang", "tablet", "ipad"]},
        4: {"keywords": ["dong ho", "watch", "smartwatch"]},
        5: {"keywords": ["tai nghe", "airpods", "headphone", "earbuds"]},
        6: {"keywords": ["may giat"]},
        7: {"keywords": ["tu lanh"]},
        8: {"keywords": ["dieu hoa", "may lanh"]},
        9: {"keywords": ["tivi", "tv", "television"]}
    }
    
    for category_id, info in category_mapping.items():
        if any(kw in keyword for kw in info["keywords"]):
            return category_id
    
    return None

def extract_price(price_text):
    """
    Trích xuất giá từ text:
    - Bỏ các ký tự không phải số
    - Chuyển về kiểu float
    """
    if not price_text:
        return 0.0
    try:
        price = ''.join(c for c in price_text if c.isdigit() or c == '.')
        return float(price)
    except:
        return 0.0

def clean_url(url, base_url=None):
    """
    Chuẩn hóa URL:
    - Thêm base_url nếu là relative URL
    - Bỏ các query params không cần thiết
    """
    if not url:
        return ""
    
    url = url.split('?')[0]
    
    if base_url and not url.startswith(('http://', 'https://')):
        return f"{base_url.rstrip('/')}/{url.lstrip('/')}"
    
    return url

def get_store_name(store_id):
    """
    Lấy tên store từ ID
    """
    store_names = {
        1: "Điện Máy Xanh",
        2: "Thế Giới Di Động",
        3: "Chợ Tốt"
    }
    return store_names.get(store_id, "Unknown")