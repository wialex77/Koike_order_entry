-- Create parts table
CREATE TABLE parts (
    id SERIAL PRIMARY KEY,
    part_number VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for parts table
CREATE INDEX idx_parts_part_number ON parts(part_number);
CREATE INDEX idx_parts_description ON parts USING gin(to_tsvector('english', description));

-- Create customers table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    state_prov VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for customers table
CREATE INDEX idx_customers_customer_id ON customers(customer_id);
CREATE INDEX idx_customers_company_name ON customers USING gin(to_tsvector('english', company_name));
