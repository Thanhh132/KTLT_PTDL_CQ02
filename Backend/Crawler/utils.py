import re

def standardize_product_name(name):
    # Chuyển thành chữ thường, xóa ký tự đặc biệt, chuẩn hóa khoảng trắng
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name)
    # Xóa các từ không liên quan
    terms_to_remove = ['chinh hang', 'moi', 'new', '2023', '2024']
    for term in terms_to_remove:
        name = name.replace(term, '')
    return name.strip()