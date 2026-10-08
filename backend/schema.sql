-- Tworzone automatycznie przy starcie backendu (CREATE TABLE IF NOT EXISTS).

-- Konta administratorów (hasła bcrypt). Dodawanie: python create_admin.py
CREATE TABLE IF NOT EXISTS users (
    username VARCHAR(100) NOT NULL PRIMARY KEY,
    password VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Jedna przeglądarka = jeden głosujący. gorka_id ustawiane po logowaniu przez Górka API.
CREATE TABLE IF NOT EXISTS voters (
    id CHAR(32) NOT NULL PRIMARY KEY,
    gorka_id VARCHAR(64) NULL,
    display_name VARCHAR(100) NULL,
    is_station TINYINT(1) NOT NULL DEFAULT 0,
    banned TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_gorka (gorka_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- open_video_id jest ustawione tylko dla otwartych propozycji, więc UNIQUE
-- pilnuje, żeby ta sama piosenka nie wisiała w kolejce dwa razy.
CREATE TABLE IF NOT EXISTS suggestions (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    video_id VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    artist VARCHAR(255) NULL,
    duration_seconds INT NULL,
    status ENUM('pending', 'approved', 'rejected', 'played') NOT NULL DEFAULT 'pending',
    reject_reason VARCHAR(255) NULL,
    submitted_by CHAR(32) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at DATETIME NULL,
    decided_by VARCHAR(100) NULL,
    played_at DATETIME NULL,
    open_video_id VARCHAR(32) GENERATED ALWAYS AS (
        CASE WHEN status IN ('pending', 'approved') THEN video_id ELSE NULL END
    ) STORED,
    UNIQUE KEY uniq_open_video (open_video_id),
    KEY idx_video (video_id),
    KEY idx_status (status),
    KEY idx_submitter (submitted_by, created_at),
    CONSTRAINT fk_suggestion_voter FOREIGN KEY (submitted_by) REFERENCES voters (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS votes (
    suggestion_id INT NOT NULL,
    voter_id CHAR(32) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (suggestion_id, voter_id),
    KEY idx_vote_voter (voter_id, created_at),
    CONSTRAINT fk_vote_suggestion FOREIGN KEY (suggestion_id) REFERENCES suggestions (id) ON DELETE CASCADE,
    CONSTRAINT fk_vote_voter FOREIGN KEY (voter_id) REFERENCES voters (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS blocklist (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    kind ENUM('video', 'artist') NOT NULL,
    value VARCHAR(255) NOT NULL,
    label VARCHAR(255) NULL,
    created_by VARCHAR(100) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_block (kind, value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tylko nadpisania. Wartości domyślne są w store.DEFAULT_SETTINGS.
CREATE TABLE IF NOT EXISTS settings (
    k VARCHAR(64) NOT NULL PRIMARY KEY,
    v VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
