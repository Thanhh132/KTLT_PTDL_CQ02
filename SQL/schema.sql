-- Tạo database TMDT nếu chưa tồn tại
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'TMDT')
BEGIN
    CREATE DATABASE TMDT;
END
GO

-- Sử dụng database TMDT
USE TMDT;
GO

-- Tạo bảng Stores (lưu thông tin cửa hàng)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Stores')
BEGIN
    CREATE TABLE Stores (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(50) NOT NULL UNIQUE,
        website NVARCHAR(500),
        created_at DATETIME DEFAULT GETDATE()
    );
END
GO

-- Tạo bảng Categories (lưu danh mục sản phẩm)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Categories')
BEGIN
    CREATE TABLE Categories (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(100) NOT NULL UNIQUE,
        created_at DATETIME DEFAULT GETDATE()
    );
END
GO

-- Tạo bảng Products (lưu thông tin sản phẩm)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Products')
BEGIN
    CREATE TABLE Products (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(255) NOT NULL,
        store_id INT NOT NULL,
        category_id INT,
        price INT NOT NULL,
        rating FLOAT,
        link NVARCHAR(500) NOT NULL,
        updated_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (store_id) REFERENCES Stores(id),
        FOREIGN KEY (category_id) REFERENCES Categories(id)
    );
END
GO

-- Tạo bảng PriceHistory (lưu lịch sử giá)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PriceHistory')
BEGIN
    CREATE TABLE PriceHistory (
        id INT IDENTITY(1,1) PRIMARY KEY,
        product_id INT NOT NULL,
        price INT NOT NULL,
        recorded_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (product_id) REFERENCES Products(id)
    );
END
GO

-- Tạo bảng Users (lưu thông tin người dùng)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Users')
BEGIN
    CREATE TABLE Users (
        id INT IDENTITY(1,1) PRIMARY KEY,
        username NVARCHAR(50) NOT NULL UNIQUE,
        email NVARCHAR(100) NOT NULL UNIQUE,
        password_hash NVARCHAR(255) NOT NULL,
        created_at DATETIME DEFAULT GETDATE()
    );
END
GO

-- Tạo bảng Favorites (lưu sản phẩm yêu thích của người dùng)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Favorites')
BEGIN
    CREATE TABLE Favorites (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL,
        product_id INT NOT NULL,
        added_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (user_id) REFERENCES Users(id),
        FOREIGN KEY (product_id) REFERENCES Products(id),
        UNIQUE (user_id, product_id) -- Đảm bảo không trùng lặp
    );
END
GO

-- Chèn dữ liệu mẫu cho Stores
INSERT INTO Stores (name, website) VALUES
    (N'Shopee', N'https://shopee.vn'),
    (N'Điện Máy Xanh', N'https://www.dienmayxanh.com'),
    (N'Thế Giới Di Động', N'https://www.thegioididong.com'),
    (N'Cellphones', N'https://cellphones.com.vn')
WHERE NOT EXISTS (SELECT 1 FROM Stores WHERE name IN (N'Shopee', N'Điện Máy Xanh', N'Thế Giới Di Động', N'Cellphones'));
GO

-- Chèn dữ liệu mẫu cho Categories
INSERT INTO Categories (name) VALUES
    (N'Điện thoại'),
    (N'Laptop'),
    (N'Máy tính bảng')
WHERE NOT EXISTS (SELECT 1 FROM Categories WHERE name IN (N'Điện thoại', N'Laptop', N'Máy tính bảng'));
GO