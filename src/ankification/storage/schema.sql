-- Cards table
CREATE TABLE IF NOT EXISTS cards (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK(type IN ('basic', 'cloze')),
    content TEXT NOT NULL,  -- JSON serialized card data
    source TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('draft', 'accepted', 'rejected')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags table
CREATE TABLE IF NOT EXISTS tags (
    card_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
    PRIMARY KEY (card_id, tag)
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    sources TEXT NOT NULL,  -- JSON array of sources
    provider TEXT NOT NULL DEFAULT 'openai',
    card_types TEXT NOT NULL DEFAULT 'basic,cloze',  -- Comma-separated
    count_guidance TEXT NOT NULL DEFAULT '10-15',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Session cards junction table
CREATE TABLE IF NOT EXISTS session_cards (
    session_id TEXT NOT NULL,
    card_id TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
    PRIMARY KEY (session_id, card_id)
);

-- Edit history table
CREATE TABLE IF NOT EXISTS edit_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT NOT NULL,
    old_content TEXT NOT NULL,
    new_content TEXT NOT NULL,
    edit_type TEXT NOT NULL CHECK(edit_type IN ('manual', 'llm_refine')),
    feedback TEXT,  -- For LLM refinements
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cards_status ON cards(status);
CREATE INDEX IF NOT EXISTS idx_cards_source ON cards(source);
CREATE INDEX IF NOT EXISTS idx_cards_created_at ON cards(created_at);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_edit_history_card_id ON edit_history(card_id);
CREATE INDEX IF NOT EXISTS idx_edit_history_timestamp ON edit_history(timestamp);
