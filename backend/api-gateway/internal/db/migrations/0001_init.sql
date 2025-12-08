CREATE TABLE users (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	email VARCHAR(255) NOT NULL UNIQUE,
	password VARCHAR(255) NOT NULL,
	name VARCHAR(255) NOT NULL,
	credits DECIMAL(10,2) DEFAULT 0.00,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE jobs (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	user_id UUID NOT NULL REFERENCES users(id),
	source_file_url TEXT NOT NULL,
	source_lang VARCHAR(10) NOT NULL,
	target_lang VARCHAR(10) NOT NULL,
	duration BIGINT NOT NULL,
	status VARCHAR(20) DEFAULT 'pending',
	cost DECIMAL(10,4),
	result_url TEXT,
	error TEXT,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	user_id UUID NOT NULL REFERENCES users(id),
	amount DECIMAL(10,4) NOT NULL,
	transaction_id VARCHAR(255) UNIQUE NOT NULL,
	source VARCHAR(50),
	previous_amount DECIMAL(10,4),
	new_amount DECIMAL(10,4),
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
