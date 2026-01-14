-- 1. Create the Database
CREATE DATABASE IF NOT EXISTS secure_bank;
USE secure_bank;

-- 2. Create the Users table (Identity)
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 3. Create the Accounts table (Money storage)
CREATE TABLE accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    account_number VARCHAR(20) UNIQUE NOT NULL,
    balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    status ENUM('active', 'suspended') DEFAULT 'active',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4. Create the Transactions table (The Ledger)
CREATE TABLE transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    account_number VARCHAR(30) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount DECIMAL(18, 2) NOT NULL,
    balance_after DECIMAL(18, 2) NOT NULL,
    related_account VARCHAR(30) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_transactions_user_created (user_id, created_at),
    INDEX idx_transactions_account_created (account_number, created_at)
);

ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255);

-- 1. First, delete the old user to avoid conflicts

USE secure_bank;

ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'customer';

ALTER TABLE users ADD COLUMN otp_code VARCHAR(6) NULL;

REPLACE INTO users (username, email, password_hash, role) 
VALUES ('admin', 'admin@example.com', 'DUMMY_HASH', 'admin');


describe users;


USE secure_bank;
ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'customer';

USE secure_bank;

-- Delete the current 'admin' record
DELETE FROM users WHERE username = 'admin';

-- Insert a new record with the EXACT hash for 'admin123'
INSERT INTO users (username, email, password_hash, role) 
VALUES (
    'admin', 
    'admin@example.com', 
    'DUMMY_HASH', 
    'admin'
);

-- Verify the change
SELECT username, password_hash FROM users WHERE username = 'admin';
UPDATE users SET role = 'admin' WHERE username = 'admin';


ALTER TABLE transactions 
MODIFY COLUMN transaction_type ENUM('deposit', 'withdrawal', 'transfer') NOT NULL;

ALTER TABLE transactions 
ADD COLUMN description VARCHAR(255) DEFAULT NULL;

ALTER TABLE transactions 
ADD COLUMN status ENUM('pending', 'completed', 'failed') DEFAULT 'completed';

ALTER TABLE users
  ADD COLUMN otp_expires_at DATETIME NULL,
  ADD COLUMN otp_attempts INT NOT NULL DEFAULT 0;
  
ALTER TABLE transactions
  ADD COLUMN user_id INT NOT NULL AFTER transaction_id;
