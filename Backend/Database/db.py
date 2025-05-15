import pyodbc
from contextlib import contextmanager

DRIVER = "{ODBC Driver 17 for SQL Server}"
SERVER = "ASUS-132\\ASUS"  # Thay bằng tên server của bạn
DATABASE = "TMDT"
CONNECTION_STRING = f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=Yes"

def create_database():
    """Tạo database TMDT nếu chưa tồn tại."""
    try:
        conn = pyodbc.connect(f"DRIVER={DRIVER};SERVER={SERVER};Trusted_Connection=Yes")
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'TMDT')
            BEGIN
                CREATE DATABASE TMDT
            END
        """)
        cursor.close()
        conn.close()
        print("Database TMDT created or already exists.")
    except Exception as e:
        print(f"Error creating database: {e}")

def get_db_connection():
    return pyodbc.connect(CONNECTION_STRING)

@contextmanager
def get_db_cursor():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def init_db():
    """Khởi tạo các bảng và dữ liệu mẫu."""
    create_database()  # Gọi trước để đảm bảo database tồn tại
    with get_db_cursor() as cursor:
        # Tạo bảng Stores
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Stores')
            CREATE TABLE Stores (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(100) NOT NULL UNIQUE,
                website NVARCHAR(500),
                created_at DATETIME DEFAULT GETDATE()
            )
        """)
        # Tạo bảng Categories
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Categories')
            CREATE TABLE Categories (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(100) NOT NULL UNIQUE,
                created_at DATETIME DEFAULT GETDATE()
            )
        """)
        # Tạo bảng Products
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Products')
            CREATE TABLE Products (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(255) NOT NULL,
                store_id INT NOT NULL,
                category_id INT,
                price DECIMAL(12,2) NOT NULL,
                rating FLOAT,
                link NVARCHAR(500) NOT NULL,
                updated_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (store_id) REFERENCES Stores(id),
                FOREIGN KEY (category_id) REFERENCES Categories(id)
            )
        """)
        # Tạo index cho Products.name
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_product_name')
            CREATE INDEX idx_product_name ON Products(name)
        """)
        # Tạo bảng PriceHistory
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PriceHistory')
            CREATE TABLE PriceHistory (
                id INT IDENTITY(1,1) PRIMARY KEY,
                product_id INT NOT NULL,
                price DECIMAL(12,2) NOT NULL,
                recorded_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (product_id) REFERENCES Products(id)
            )
        """)
        # Tạo bảng Users
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Users')
            CREATE TABLE Users (
                id INT IDENTITY(1,1) PRIMARY KEY,
                username NVARCHAR(50) NOT NULL UNIQUE,
                email NVARCHAR(100) NOT NULL UNIQUE,
                password_hash NVARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT GETDATE(),
                is_active BIT DEFAULT 1
            )
        """)
        # Tạo bảng Favorites
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Favorites')
            CREATE TABLE Favorites (
                id INT IDENTITY(1,1) PRIMARY KEY,
                user_id INT NOT NULL,
                product_id INT NOT NULL,
                added_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (user_id) REFERENCES Users(id),
                FOREIGN KEY (product_id) REFERENCES Products(id),
                UNIQUE (user_id, product_id)
            )
        """)
        # Chèn dữ liệu mẫu cho Stores
        cursor.execute("""
            INSERT INTO Stores (name, website)
            SELECT name, website
            FROM (VALUES
                (N'Shopee', N'https://shopee.vn'),
                (N'Điện Máy Xanh', N'https://www.dienmayxanh.com'),
                (N'Thế Giới Di Động', N'https://www.thegioididong.com'),
                (N'Cellphones', N'https://cellphones.com.vn')
            ) AS src(name, website)
            WHERE NOT EXISTS (SELECT 1 FROM Stores WHERE name = src.name)
        """)
        # Chèn dữ liệu mẫu cho Categories
        cursor.execute("""
            INSERT INTO Categories (name)
            SELECT name
            FROM (VALUES
                (N'Điện thoại'),
                (N'Laptop'),
                (N'Máy tính bảng')
            ) AS src(name)
            WHERE NOT EXISTS (SELECT 1 FROM Categories WHERE name = src.name)
        """)