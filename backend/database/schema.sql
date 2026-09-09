CREATE TABLE IF NOT EXISTS variants (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	gene TEXT NOT NULL CHECK (length(trim(gene)) > 0),
	hgvs_notation TEXT NOT NULL CHECK (length(trim(hgvs_notation)) > 0),
	UNIQUE (gene, hgvs_notation)
);

CREATE TABLE IF NOT EXISTS variant_evidence (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	variant_id INTEGER NOT NULL,
	evidence_id TEXT NOT NULL CHECK (length(trim(evidence_id)) > 0),
	criterion TEXT NOT NULL CHECK (
		criterion IN ('BP4', 'BS1', 'PM2', 'PP3', 'PS3')
	),
	strength TEXT NOT NULL CHECK (
		strength IN ('supporting', 'moderate', 'strong', 'very_strong', 'stand_alone')
	),
	direction TEXT NOT NULL CHECK (
		direction IN ('pathogenic', 'benign')
	),
	source_name TEXT NOT NULL CHECK (length(trim(source_name)) > 0),
	source_reference TEXT,
	summary TEXT NOT NULL CHECK (length(trim(summary)) > 0),
	FOREIGN KEY (variant_id) REFERENCES variants(id) ON DELETE RESTRICT,
	UNIQUE (variant_id, evidence_id)
);

PRAGMA user_version = 3;
