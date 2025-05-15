from datetime import datetime

class Product:
    def __init__(self, name, store_id, price, rating, link, category_id=None, updated_at=None):
        self.name = name
        self.store_id = store_id
        self.category_id = category_id
        self.price = price
        self.rating = rating
        self.link = link
        self.updated_at = updated_at or datetime.now()

    def to_dict(self):
        return {
            "name": self.name,
            "store_id": self.store_id,
            "category_id": self.category_id,
            "price": self.price,
            "rating": self.rating,
            "link": self.link,
            "updated_at": self.updated_at.isoformat()
        }