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

-- 9. Chèn dữ liệu mẫu cho Stores
IF NOT EXISTS (SELECT 1 FROM Stores WHERE name = N'Điện Máy Xanh')
    INSERT INTO Stores (id, name, website) VALUES (1, N'Điện Máy Xanh', N'https://www.dienmayxanh.com');

IF NOT EXISTS (SELECT 1 FROM Stores WHERE name = N'Thế Giới Di Động')
    INSERT INTO Stores (id, name, website) VALUES (2, N'Thế Giới Di Động', N'https://www.thegioididong.com');

IF NOT EXISTS (SELECT 1 FROM Stores WHERE name = N'Chợ Tốt')
    INSERT INTO Stores (id, name, website) VALUES (3, N'Chợ Tốt', N'https://chotot.com');
GO

-- 10. Chèn dữ liệu mẫu cho Categories
IF NOT EXISTS (SELECT 1 FROM Categories WHERE name = N'Điện thoại')
    INSERT INTO Categories (name) VALUES (N'Điện thoại');

IF NOT EXISTS (SELECT 1 FROM Categories WHERE name = N'Laptop')
    INSERT INTO Categories (name) VALUES (N'Laptop');

IF NOT EXISTS (SELECT 1 FROM Categories WHERE name = N'Máy tính bảng')
    INSERT INTO Categories (name) VALUES (N'Máy tính bảng');

IF NOT EXISTS (SELECT 1 FROM Categories WHERE name = N'Sạc')
    INSERT INTO Categories (name) VALUES (N'Sạc');

IF NOT EXISTS (SELECT 1 FROM Categories WHERE name = N'Tai nghe')
    INSERT INTO Categories (name) VALUES (N'Tai nghe');

IF NOT EXISTS (SELECT 1 FROM Categories WHERE name = N'Pin dự phòng')
    INSERT INTO Categories (name) VALUES (N'Pin dự phòng');

IF NOT EXISTS (SELECT 1 FROM Categories WHERE name = N'Ốp lưng')
    INSERT INTO Categories (name) VALUES (N'Ốp lưng');

IF NOT EXISTS (SELECT 1 FROM Categories WHERE name = N'Chuột máy tính')
    INSERT INTO Categories (name) VALUES (N'Chuột máy tính');

IF NOT EXISTS (SELECT 1 FROM Categories WHERE name = N'Bàn phím')
    INSERT INTO Categories (name) VALUES (N'Bàn phím');

IF NOT EXISTS (SELECT 1 FROM Categories WHERE name = N'Màn hình máy tính')
    INSERT INTO Categories (name) VALUES (N'Màn hình máy tính');

IF NOT EXISTS (SELECT 1 FROM Categories WHERE name = N'Thiết bị mạng')
    INSERT INTO Categories (name) VALUES (N'Thiết bị mạng');
GO