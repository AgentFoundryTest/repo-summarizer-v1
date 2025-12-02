-- Migration: Add status column
ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active';
