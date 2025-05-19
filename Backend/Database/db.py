import pyodbc
import logging
import os
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Thông tin kết nối database
DB_SERVER = 'ASUS-132\\ASUS'
DB_NAME = 'TMDR'
DB_TRUSTED_CONNECTION = 'yes'
DB_DRIVER = 'ODBC Driver 17 for SQL Server'

def get_connection_string() -> str:
    """Tạo chuỗi kết nối database."""
    return f'DRIVER={{{DB_DRIVER}}};SERVER={DB_SERVER};DATABASE=master;Trusted_Connection={DB_TRUSTED_CONNECTION};charset=UTF8'

def create_database():
    """Tạo database nếu chưa tồn tại."""
    try:
        # Kết nối đến master database trước
        conn = pyodbc.connect(get_connection_string())
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Kiểm tra và tạo database TMDR
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'TMDR')
            BEGIN
                CREATE DATABASE TMDR
            END
        """)
        
        cursor.close()
        conn.close()
        logger.info("Database TMDR created or already exists.")
    except Exception as e:
        logger.error(f"Lỗi khi tạo database: {str(e)}")
        raise

def get_db_connection_string() -> str:
    """Tạo chuỗi kết nối đến database TMDR."""
    return f'DRIVER={{{DB_DRIVER}}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection={DB_TRUSTED_CONNECTION};charset=UTF8'

@contextmanager
def get_db_cursor():
    """Context manager để quản lý kết nối database."""
    conn = None
    cursor = None
    try:
        conn = pyodbc.connect(get_db_connection_string())
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
    """Khởi tạo database và các bảng cần thiết."""
    try:
        # Đảm bảo database tồn tại
        create_database()
        
        with get_db_cursor() as cursor:
            # Tạo bảng Users nếu chưa tồn tại
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Users')
                BEGIN
                    CREATE TABLE Users (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        username NVARCHAR(50) NOT NULL,
                        created_at DATETIME DEFAULT GETDATE()
                    )
                END
            """)

            # Thêm user mặc định nếu chưa có
            cursor.execute("IF NOT EXISTS (SELECT * FROM Users WHERE id = 1) BEGIN SET IDENTITY_INSERT Users ON; INSERT INTO Users (id, username) VALUES (1, 'default_user'); SET IDENTITY_INSERT Users OFF; END")

            # Tạo bảng Stores nếu chưa tồn tại
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Stores')
                BEGIN
                    CREATE TABLE Stores (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        name NVARCHAR(100) NOT NULL,
                        url NVARCHAR(255)
                    )
                END
            """)

            # Thêm các cửa hàng mặc định nếu chưa có
            cursor.execute("IF NOT EXISTS (SELECT * FROM Stores) BEGIN INSERT INTO Stores (name, url) VALUES ('Điện Máy Xanh', 'https://www.dienmayxanh.com'), ('Thế Giới Di Động', 'https://www.thegioididong.com'), ('Chợ Tốt', 'https://www.chotot.com') END")

            # Tạo bảng Products nếu chưa tồn tại
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Products')
                BEGIN
                    CREATE TABLE Products (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        name NVARCHAR(255) NOT NULL,
                        price DECIMAL(18,2) NOT NULL,
                        store_id INT FOREIGN KEY REFERENCES Stores(id),
                        category_id INT,
                        link NVARCHAR(MAX),
                        image_url NVARCHAR(MAX),
                        condition NVARCHAR(50),
                        rating FLOAT,
                        last_updated DATETIME DEFAULT GETDATE()
                    )
                END
            """)

            # Tạo bảng Favorites nếu chưa tồn tại
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Favorites')
                BEGIN
                    CREATE TABLE Favorites (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        user_id INT FOREIGN KEY REFERENCES Users(id),
                        product_id INT FOREIGN KEY REFERENCES Products(id),
                        created_at DATETIME DEFAULT GETDATE(),
                        UNIQUE (user_id, product_id)
                    )
                END
            """)

            # Tạo bảng PriceHistory nếu chưa tồn tại
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PriceHistory')
                BEGIN
                    CREATE TABLE PriceHistory (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        product_id INT FOREIGN KEY REFERENCES Products(id),
                        price DECIMAL(18,2) NOT NULL,
                        recorded_at DATETIME DEFAULT GETDATE()
                    )
                END
            """)

            # Tạo bảng SearchHistory nếu chưa tồn tại
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'SearchHistory')
                BEGIN
                    CREATE TABLE SearchHistory (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        query NVARCHAR(255) NOT NULL,
                        user_id INT FOREIGN KEY REFERENCES Users(id),
                        searched_at DATETIME DEFAULT GETDATE()
                    )
                END
            """)

            # Tạo bảng Notifications nếu chưa tồn tại
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Notifications')
                BEGIN
                    CREATE TABLE Notifications (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        product_id INT FOREIGN KEY REFERENCES Products(id),
                        message NVARCHAR(MAX) NOT NULL,
                        is_read BIT DEFAULT 0,
                        created_at DATETIME DEFAULT GETDATE()
                    )
                END
            """)

            logger.info("Đã khởi tạo database thành công")
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo database: {str(e)}")
        raise

def save_products(products: List[Dict[str, Any]], search_query: str):
    """Lưu danh sách sản phẩm vào database."""
    try:
        with get_db_cursor() as cursor:
            # Lưu từng sản phẩm
            logger.info(f"Bắt đầu lưu {len(products)} sản phẩm vào database")
            for product in products:
                try:
                    # Kiểm tra sản phẩm đã tồn tại
                    cursor.execute("""
                        SELECT id, price FROM Products 
                        WHERE name = ? AND store_id = ? AND link = ?
                    """, (product['name'], product['store_id'], product['link']))
                    existing_product = cursor.fetchone()
                    
                    if existing_product:
                        # Cập nhật sản phẩm và lưu lịch sử giá
                        product_id = existing_product[0]
                        old_price = existing_product[1]
                        
                        if old_price != product['price']:
                            # Cập nhật sản phẩm
                            cursor.execute("""
                                UPDATE Products 
                                SET price = ?, 
                                    rating = ?,
                                    image_url = ?,
                                    last_updated = GETDATE()
                                WHERE id = ?
                            """, (
                                product['price'],
                                product.get('rating'),
                                product.get('image_url'),
                                product_id
                            ))
                            
                            # Lưu lịch sử giá
                            cursor.execute("""
                                INSERT INTO PriceHistory (product_id, price)
                                VALUES (?, ?)
                            """, (product_id, product['price']))

                            # Tạo thông báo thay đổi giá
                            price_change = product['price'] - old_price
                            cursor.execute("""
                                INSERT INTO Notifications (product_id, message)
                                VALUES (?, ?)
                            """, (
                                product_id,
                                f"Giá sản phẩm {product['name']} đã thay đổi từ {old_price:,.0f}đ thành {product['price']:,.0f}đ"
                            ))
                    else:
                        # Thêm sản phẩm mới
                        cursor.execute("""
                            INSERT INTO Products (name, price, store_id, link, image_url, rating, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?, GETDATE())
                        """, (
                            product['name'],
                            product['price'],
                            product['store_id'],
                            product['link'],
                            product.get('image_url'),
                            product.get('rating')
                        ))
                        
                        # Lấy ID của sản phẩm vừa thêm
                        cursor.execute("SELECT @@IDENTITY")
                        product_id = cursor.fetchone()[0]
                        
                        # Lưu lịch sử giá cho sản phẩm mới
                        cursor.execute("""
                            INSERT INTO PriceHistory (product_id, price)
                            VALUES (?, ?)
                        """, (product_id, product['price']))
                        
                except Exception as e:
                    logger.error(f"Lỗi khi lưu sản phẩm {product.get('name', 'Unknown')}: {str(e)}")
                    continue  # Tiếp tục với sản phẩm tiếp theo
                    
            # Lưu lịch sử tìm kiếm
            cursor.execute("""
                INSERT INTO SearchHistory (query, user_id)
                VALUES (?, 1)  -- Sử dụng user_id mặc định là 1
            """, (search_query,))
            
            logger.info("Đã lưu sản phẩm và lịch sử tìm kiếm thành công")
    except Exception as e:
        logger.error(f"Lỗi khi lưu sản phẩm vào database: {str(e)}")
        raise

def clear_history():
    """Xóa lịch sử sản phẩm và giá, nhưng giữ lại các sản phẩm trong Favorites."""
    try:
        with get_db_cursor() as cursor:
            # Xóa lịch sử giá của các sản phẩm không nằm trong Favorites
            cursor.execute("""
                DELETE FROM PriceHistory 
                WHERE product_id IN (
                    SELECT p.id 
                    FROM Products p 
                    LEFT JOIN Favorites f ON p.id = f.product_id 
                    WHERE f.product_id IS NULL
                )
            """)
            
            # Xóa các sản phẩm không nằm trong Favorites
            cursor.execute("""
                DELETE FROM Products 
                WHERE id NOT IN (
                    SELECT DISTINCT product_id 
                    FROM Favorites
                )
            """)
            
            logger.info("Đã xóa lịch sử sản phẩm thành công, giữ lại các sản phẩm yêu thích")
            return True
    except Exception as e:
        logger.error(f"Lỗi khi xóa lịch sử sản phẩm: {str(e)}")
        raise

def create_price_change_notification(product_id: int, old_price: float, new_price: float):
    """Tạo thông báo khi giá sản phẩm thay đổi."""
    try:
        with get_db_cursor() as cursor:
            # Lấy thông tin sản phẩm
            cursor.execute("""
                SELECT name FROM Products WHERE id = ?
            """, (product_id,))
            product = cursor.fetchone()
            
            if product:
                price_change = new_price - old_price
                message = f"Giá sản phẩm {product[0]} đã thay đổi từ {old_price:,.0f}đ thành {new_price:,.0f}đ"
                
                # Tạo thông báo
                cursor.execute("""
                    INSERT INTO Notifications (
                        product_id, message, price_change,
                        old_price, new_price
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    product_id,
                    message,
                    price_change,
                    old_price,
                    new_price
                ))
                
                logger.info(f"Đã tạo thông báo thay đổi giá cho sản phẩm {product_id}")
            else:
                logger.warning(f"Không tìm thấy sản phẩm với ID {product_id}")
                
    except Exception as e:
        logger.error(f"Lỗi khi tạo thông báo thay đổi giá: {str(e)}")
        raise