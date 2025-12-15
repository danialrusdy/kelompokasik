-- Database Schema for SPK Customer Segmentation

-- 1. Table Users (Admin)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'admin'
);

-- 2. Table Customers (Raw Data)
CREATE TABLE IF NOT EXISTS customers (
    CustomerID INT PRIMARY KEY,
    Gender VARCHAR(10),
    Age INT,
    AnnualIncome INT,
    SpendingScore INT
);

-- 3. Table Preprocessing Data (Scaled)
CREATE TABLE IF NOT EXISTS preprocessing_data (
    CustomerID INT PRIMARY KEY,
    AnnualIncome_Scaled FLOAT,
    SpendingScore_Scaled FLOAT,
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID) ON DELETE CASCADE
);

-- 4. Table Clustering Results
CREATE TABLE IF NOT EXISTS clustering_results (
    CustomerID INT PRIMARY KEY,
    Cluster INT,
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID) ON DELETE CASCADE
);

-- Initial Admin Insert (Password: sandinyasusah)
-- Note: The password hash here is a placeholder. You should generate a real bcrypt hash in Python.
-- For now, we will insert a user if not exists handled by application logic or manual setup.
-- But here is a template command:
-- INSERT INTO users (username, password_hash) VALUES ('kelompokasik', '$2b$12$...'); 
