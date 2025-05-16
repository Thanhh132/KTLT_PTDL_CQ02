import pyodbc
import logging
from contextlib import contextmanager

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cấu hình kết nối database
connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ASUS-132\\ASUS;"
    "DATABASE=TMDR;"
    "Trusted_Connection=yes;"
)

def create_database():
    """Tạo database nếu chưa tồn tại."""
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=ASUS-132\\ASUS;"
            "Trusted_Connection=yes;"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute("IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'TMDR') CREATE DATABASE TMDR")
        cursor.close()
        conn.close()
        logger.info("Database TMDR created or already exists.")
    except Exception as e:
        logger.error(f"Lỗi khi tạo database: {str(e)}")
        raise

@contextmanager
def get_db_cursor():
    """Context manager để quản lý kết nối database."""
    conn = None
    cursor = None
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def init_db():
    """Khởi tạo các bảng và dữ liệu mẫu nếu chưa tồn tại."""
    create_database()
    with get_db_cursor() as cursor:
        # Tạo bảng Stores với ID cố định
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Stores')
            BEGIN
                CREATE TABLE Stores (
                    id INT PRIMARY KEY,
                    name NVARCHAR(100) NOT NULL UNIQUE,
                    website NVARCHAR(500),
                    created_at DATETIME DEFAULT GETDATE()
                )
            END
        """)

        # Tạo bảng Categories
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Categories')
            BEGIN
                CREATE TABLE Categories (
                    id INT PRIMARY KEY,  -- Cố định ID
                    name NVARCHAR(100) NOT NULL UNIQUE,
                    created_at DATETIME DEFAULT GETDATE()
                )
            END
        """)

        # Tạo bảng Products (category_id cho phép NULL)
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Products')
            BEGIN
                CREATE TABLE Products (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    name NVARCHAR(255) NOT NULL,
                    store_id INT NOT NULL,
                    category_id INT NULL,
                    price DECIMAL(15,2) NOT NULL,
                    rating FLOAT,
                    link NVARCHAR(500) NOT NULL,
                    image_url NVARCHAR(500),
                    updated_at DATETIME DEFAULT GETDATE(),
                    FOREIGN KEY (store_id) REFERENCES Stores(id),
                    FOREIGN KEY (category_id) REFERENCES Categories(id)
                )
            END
        """)

        # Tạo các indexes
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_product_name')
            BEGIN
                CREATE INDEX idx_product_name ON Products(name)
            END
        """)
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_product_price')
            BEGIN
                CREATE INDEX idx_product_price ON Products(price)
            END
        """)

        # Tạo bảng PriceHistory
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PriceHistory')
            BEGIN
                CREATE TABLE PriceHistory (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    product_id INT NOT NULL,
                    price DECIMAL(15,2) NOT NULL,
                    recorded_at DATETIME DEFAULT GETDATE(),
                    FOREIGN KEY (product_id) REFERENCES Products(id)
                )
            END
        """)

        # Thêm dữ liệu mẫu vào bảng Stores nếu chưa có
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM Stores)
            BEGIN
                INSERT INTO Stores (id, name, website)
                VALUES 
                    (1, N'Điện Máy Xanh', N'https://www.dienmayxanh.com'),
                    (2, N'Thế Giới Di Động', N'https://www.thegioididong.com'),
                    (3, N'Chợ Tốt', N'https://chotot.com')
            END
        """)

        # Thêm dữ liệu mẫu vào bảng Categories nếu chưa có
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM Categories)
            BEGIN
                INSERT INTO Categories (id, name)
                VALUES 
                    (1, N'Điện thoại'),
                    (2, N'Laptop'),
                    (3, N'Máy tính bảng'),
                    (4, N'Tai nghe'),
                    (5, N'Tivi')
            END
        """)

        logger.info("Database tables and initial data have been created successfully.")

def get_category_id(cursor, product_name):
    """Lấy category_id dựa trên từ khóa tìm kiếm."""
    categories = {
        'dien thoai': 'Điện thoại',
        'laptop': 'Laptop',
        'may tinh bang': 'Máy tính bảng',
        'tai nghe': 'Tai nghe',
        'tivi': 'Tivi'
    }
    product_name_lower = product_name.lower().strip()
    for keyword, category_name in categories.items():
        if keyword in product_name_lower:
            cursor.execute("SELECT id FROM Categories WHERE name = ?", (category_name,))
            result = cursor.fetchone()
            if result:
                return result[0]
    return None

def save_products(products, product_name=""):
    """Lưu sản phẩm vào bảng Products và PriceHistory."""
    logger.info(f"Bắt đầu lưu {len(products)} sản phẩm vào database")

    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT id, name FROM Stores")
            stores = cursor.fetchall()
            logger.info("Store IDs in database:")
            for store in stores:
                logger.info(f"Store ID: {store[0]} - Name: {store[1]}")

            # Lấy category_id dựa trên từ khóa tìm kiếm
            default_category_id = get_category_id(cursor, product_name)

            for product in products:
                try:
                    logger.debug(f"Xử lý sản phẩm: {product}")
                    if not product.get('name') or not product.get('link') or not product.get('price'):
                        logger.warning(f"Bỏ qua sản phẩm thiếu thông tin: {product}")
                        continue

                    cursor.execute("SELECT 1 FROM Stores WHERE id = ?", (product['store_id'],))
                    if not cursor.fetchone():
                        logger.error(f"Store ID không hợp lệ: {product['store_id']} cho sản phẩm {product['name']}")
                        continue

                    # Gán category_id nếu không có
                    category_id = product.get('category_id', default_category_id)

                    cursor.execute("""
                        SELECT id, price FROM Products 
                        WHERE link = ? AND store_id = ?
                    """, (product['link'], product['store_id']))
                    existing_product = cursor.fetchone()

                    if existing_product:
                        product_id = existing_product[0]
                        old_price = existing_product[1]

                        if old_price != product['price']:
                            logger.info(f"Cập nhật sản phẩm ID {product_id}: {product['name']}")
                            cursor.execute("""
                                UPDATE Products 
                                SET name = ?, price = ?, rating = ?, image_url = ?, updated_at = GETDATE(), category_id = ?
                                WHERE id = ?
                            """, (product['name'], product['price'], product.get('rating', 0.0), 
                                  product.get('image_url', ''), category_id, product_id))

                            cursor.execute("""
                                INSERT INTO PriceHistory (product_id, price)
                                VALUES (?, ?)
                            """, (product_id, product['price']))
                            logger.info(f"Đã cập nhật giá mới cho sản phẩm ID {product_id}")
                    else:
                        logger.info(f"Thêm sản phẩm mới: {product['name']}")
                        cursor.execute("""
                            INSERT INTO Products (name, store_id, category_id, price, rating, link, image_url)
                            OUTPUT INSERTED.ID
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (product['name'], product['store_id'], category_id, 
                              product['price'], product.get('rating', 0.0), product['link'], 
                              product.get('image_url', '')))

                        row = cursor.fetchone()
                        if row:
                            product_id = row[0]
                            logger.info(f"Đã thêm sản phẩm mới với ID {product_id}")

                            cursor.execute("""
                                INSERT INTO PriceHistory (product_id, price)
                                VALUES (?, ?)
                            """, (product_id, product['price']))
                            logger.info(f"Đã thêm lịch sử giá cho sản phẩm ID {product_id}")
                        else:
                            logger.error(f"Không lấy được ID sau khi thêm sản phẩm: {product['name']}")

                except Exception as e:
                    logger.error(f"Lỗi khi lưu sản phẩm {product.get('name', 'Unknown')}: {str(e)}")
                    continue
    except Exception as e:
        logger.error(f"Lỗi khi kết nối database: {str(e)}")
        raise

def clear_history():
    """Xóa toàn bộ dữ liệu từ bảng PriceHistory và Products."""
    try:
        with get_db_cursor() as cursor:
            # Xóa dữ liệu từ bảng PriceHistory trước vì có khóa ngoại
            cursor.execute("DELETE FROM PriceHistory")
            logger.info("Đã xóa dữ liệu từ bảng PriceHistory")
            
            # Xóa dữ liệu từ bảng Products
            cursor.execute("DELETE FROM Products")
            logger.info("Đã xóa dữ liệu từ bảng Products")
            
            # Reset identity cho bảng Products
            cursor.execute("DBCC CHECKIDENT ('Products', RESEED, 0)")
            cursor.execute("DBCC CHECKIDENT ('PriceHistory', RESEED, 0)")
            logger.info("Đã reset identity cho các bảng")
    except Exception as e:
        logger.error(f"Lỗi khi xóa lịch sử: {str(e)}")
        raise