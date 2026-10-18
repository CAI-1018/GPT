CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    observed_on TEXT,
    source TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','historical','needs_confirmation')),
    confidence TEXT NOT NULL CHECK(confidence IN ('reported','inferred')),
    sensitivity TEXT NOT NULL CHECK(sensitivity IN ('personal','sensitive')),
    review_on TEXT,
    supersedes TEXT
);
CREATE INDEX IF NOT EXISTS memory_category_status ON memories(category,status);
