-- 1. Tạo database TMDR nếu chưa tồn tại
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'TMDR')
BEGIN
    CREATE DATABASE TMDR;
END
GO

-- 2. Sử dụng database TMDR
USE TMDR;
GO

-- 3. Tạo bảng Stores với ID cố định
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Stores')
BEGIN
    CREATE TABLE Stores (
        id INT PRIMARY KEY,  -- Bỏ IDENTITY
        name NVARCHAR(100) NOT NULL UNIQUE,
        website NVARCHAR(500),
        created_at DATETIME DEFAULT GETDATE()
    );
END
GO

-- 4. Tạo bảng Categories
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Categories')
BEGIN
    CREATE TABLE Categories (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(100) NOT NULL UNIQUE,
        created_at DATETIME DEFAULT GETDATE()
    );
END
GO

-- 5. Tạo bảng Products với price là DECIMAL(15,2)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Products')
BEGIN
    CREATE TABLE Products (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(255) NOT NULL,
        store_id INT NOT NULL,
        category_id INT,
        price DECIMAL(15,2) NOT NULL,
        rating FLOAT,
        link NVARCHAR(500) NOT NULL,
        image_url NVARCHAR(500),
        updated_at DATETIME DEFAULT GETDATE(),
        last_updated DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (store_id) REFERENCES Stores(id),
        FOREIGN KEY (category_id) REFERENCES Categories(id)
    );
END
ELSE
BEGIN
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE name = 'image_url' AND object_id = OBJECT_ID('Products'))
    BEGIN
        ALTER TABLE Products ADD image_url NVARCHAR(500);
    END
    IF EXISTS (SELECT * FROM sys.columns WHERE name = 'price' AND object_id = OBJECT_ID('Products') AND system_type_id = TYPE_ID('int'))
    BEGIN
        ALTER TABLE Products ALTER COLUMN price DECIMAL(15,2) NOT NULL;
    END
END
GO

-- 6. Tạo bảng PriceHistory
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PriceHistory')
BEGIN
    CREATE TABLE PriceHistory (
        id INT IDENTITY(1,1) PRIMARY KEY,
        product_id INT NOT NULL,
        price DECIMAL(15,2) NOT NULL,
        recorded_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (product_id) REFERENCES Products(id)
    );
END
GO

-- 7. Tạo bảng Users
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Users')
BEGIN
    CREATE TABLE Users (
        id INT IDENTITY(1,1) PRIMARY KEY,
        username NVARCHAR(50) NOT NULL UNIQUE,
        email NVARCHAR(100) NOT NULL UNIQUE,
        password_hash NVARCHAR(255) NOT NULL,
        created_at DATETIME DEFAULT GETDATE(),
        is_active BIT DEFAULT 1
    );
END
GO

-- 8. Tạo bảng Favorites
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Favorites')
BEGIN
    CREATE TABLE Favorites (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL,
        product_id INT NOT NULL,
        added_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (user_id) REFERENCES Users(id),
        FOREIGN KEY (product_id) REFERENCES Products(id),
        UNIQUE (user_id, product_id)
    );
END
GO

-- 9. Tạo bảng Notifications
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Notifications')
BEGIN
    CREATE TABLE Notifications (
        id INT IDENTITY(1,1) PRIMARY KEY,
        product_id INT NOT NULL,
        message NVARCHAR(500) NOT NULL,
        price_change DECIMAL(15,2) NOT NULL,
        old_price DECIMAL(15,2) NOT NULL,
        new_price DECIMAL(15,2) NOT NULL,
        created_at DATETIME DEFAULT GETDATE(),
        is_read BIT DEFAULT 0,
        FOREIGN KEY (product_id) REFERENCES Products(id)
    );
END
GO

-- 10. Tạo bảng SearchHistory
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'SearchHistory')
BEGIN
    CREATE TABLE SearchHistory (
        id INT IDENTITY(1,1) PRIMARY KEY,
        search_query NVARCHAR(255) NOT NULL,
        search_date DATETIME DEFAULT GETDATE(),
        results_count INT DEFAULT 0
    );
END
GO

-- 11. Chèn dữ liệu cho bảng Categories nếu chưa có
IF NOT EXISTS (SELECT * FROM Categories WHERE name IN (
    N'Điện thoại', N'Laptop', N'Máy tính bảng', N'Tai nghe',
    N'Tivi', N'Máy hút bụi', N'Máy giặt', N'Tủ lạnh',
    N'Điều hòa', N'Nồi cơm điện', N'Khác'
))
BEGIN
    -- Xóa dữ liệu cũ nếu có
    DELETE FROM Categories;
    
    -- Reset identity
    DBCC CHECKIDENT ('Categories', RESEED, 0);
    
    -- Chèn các danh mục mới
    INSERT INTO Categories (name) VALUES
    (N'Điện thoại'),      -- ID: 1
    (N'Laptop'),          -- ID: 2
    (N'Máy tính bảng'),   -- ID: 3
    (N'Tai nghe'),        -- ID: 4
    (N'Tivi'),            -- ID: 5
    (N'Máy hút bụi'),     -- ID: 6
    (N'Máy giặt'),        -- ID: 7
    (N'Tủ lạnh'),         -- ID: 8
    (N'Điều hòa'),        -- ID: 9
    (N'Nồi cơm điện'),    -- ID: 10
    (N'Khác');           -- ID: 11
END
GO