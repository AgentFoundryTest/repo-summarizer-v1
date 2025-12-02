-- User management queries
-- Get active users
SELECT * FROM users WHERE status = 'active';

-- Count users by status
SELECT status, COUNT(*) as count 
FROM users 
GROUP BY status;
