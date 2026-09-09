CREATE TABLE IF NOT EXISTS variants (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	gene TEXT NOT NULL CHECK (length(trim(gene)) > 0),
	hgvs_notation TEXT NOT NULL CHECK (length(trim(hgvs_notation)) > 0),
	UNIQUE (gene, hgvs_notation)
);

PRAGMA user_version = 2;
