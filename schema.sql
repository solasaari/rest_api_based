CREATE TABLE IF NOT EXISTS tasks_data
(
    task_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    task_creation_ts TIMESTAMP DEFAULT (CURRENT_TIMESTAMP),
    task_description TEXT,
    is_closed        BOOLEAN
);

CREATE VIEW IF NOT EXISTS tasks_counts AS
SELECT COUNT(*)       as total_tasks,
       SUM(is_closed) as closed_tasks
FROM tasks_data;