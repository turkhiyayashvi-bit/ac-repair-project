-- ==========================================
-- AC SERVICE & PCB REPAIR DATABASE
-- PART 1
-- ==========================================


-- ==========================================
-- BRANDS
-- ==========================================

CREATE TABLE brands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    logo_image VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);


-- ==========================================
-- AC ERROR CODES
-- ==========================================

CREATE TABLE ac_error_codes (
    id INT AUTO_INCREMENT PRIMARY KEY,

    brand_id INT NOT NULL,

    code VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    image VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (brand_id)
        REFERENCES brands(id)
);


-- ==========================================
-- PCB COMPANIES
-- ==========================================

CREATE TABLE pcb_companies (
    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(150) NOT NULL,
    logo VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);


-- ==========================================
-- PCB MODELS
-- ==========================================

CREATE TABLE pcb_models (
    id INT AUTO_INCREMENT PRIMARY KEY,

    pcb_company_id INT NOT NULL,

    name VARCHAR(150) NOT NULL,
    photo VARCHAR(255),
    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (pcb_company_id)
        REFERENCES pcb_companies(id)
);


-- ==========================================
-- PCB MODEL BRANDS
-- ==========================================

CREATE TABLE pcb_model_brands (
    id INT AUTO_INCREMENT PRIMARY KEY,

    pcb_model_id INT NOT NULL,
    brand_id INT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (pcb_model_id)
        REFERENCES pcb_models(id),

    FOREIGN KEY (brand_id)
        REFERENCES brands(id)
);


-- ==========================================
-- PCB ERROR CODES
-- ==========================================

CREATE TABLE pcb_error_codes (
    id INT AUTO_INCREMENT PRIMARY KEY,

    pcb_model_id INT NOT NULL,

    code VARCHAR(50) NOT NULL,
    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (pcb_model_id)
        REFERENCES pcb_models(id)
);


-- ==========================================
-- TECHNICIANS
-- ==========================================

CREATE TABLE technicians (
    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL UNIQUE,
    city VARCHAR(100),
    state VARCHAR(100),
    shop_name VARCHAR(150),
    google_id VARCHAR(255),

    is_email_verified BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,
    marketing_consent BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);
-- =========================
-- OTP TABLE
-- =========================

CREATE TABLE otps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    code VARCHAR(6) NOT NULL,
    expires_at DATETIME NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =========================
-- USERS TABLE
-- =========================

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =========================
-- ROLES TABLE
-- =========================

CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);


-- =========================
-- PERMISSIONS TABLE
-- =========================

CREATE TABLE permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);


-- =========================
-- ROLE PERMISSIONS TABLE
-- =========================

CREATE TABLE role_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_id INT NOT NULL,
    permission_id INT NOT NULL,

    FOREIGN KEY (role_id)
    REFERENCES roles(id)
    ON DELETE CASCADE,

    FOREIGN KEY (permission_id)
    REFERENCES permissions(id)
    ON DELETE CASCADE
);


-- =========================
-- REPAIR JOBS TABLE
-- =========================

CREATE TABLE repair_jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    technician_id INT,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (technician_id)
    REFERENCES technicians(id)
    ON DELETE SET NULL
);


-- =========================
-- REPAIR STATUS HISTORY
-- =========================

CREATE TABLE repair_status_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    repair_job_id INT NOT NULL,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (repair_job_id)
    REFERENCES repair_jobs(id)
    ON DELETE CASCADE
);


-- =========================
-- REPORTS TABLE
-- =========================

CREATE TABLE reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    technician_id INT,
    repair_job_id INT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (technician_id)
    REFERENCES technicians(id)
    ON DELETE SET NULL,

    FOREIGN KEY (repair_job_id)
    REFERENCES repair_jobs(id)
    ON DELETE SET NULL
);


-- =========================
-- SETTINGS TABLE
-- =========================

CREATE TABLE settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    value TEXT
);


-- =========================
-- FOREIGN KEYS FOR PCB RELATIONS
-- =========================

CREATE TABLE pcb_model_brands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pcb_model_id INT NOT NULL,
    brand_id INT NOT NULL,

    FOREIGN KEY (pcb_model_id)
    REFERENCES pcb_models(id)
    ON DELETE CASCADE,

    FOREIGN KEY (brand_id)
    REFERENCES brands(id)
    ON DELETE CASCADE
);