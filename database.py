import sqlite3
import os

DB_PATH = "gaming_bot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            discord_id TEXT PRIMARY KEY,
            discord_name TEXT,
            lol_username TEXT,
            lol_tag TEXT,
            tft_username TEXT,
            tft_tag TEXT,
            valorant_username TEXT,
            valorant_tag TEXT,
            steam_id TEXT,
            wow_character TEXT,
            wow_realm TEXT,
            wow_region TEXT DEFAULT 'eu',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def register_game(discord_id, discord_name, game, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO users (discord_id, discord_name)
        VALUES (?, ?)
        ON CONFLICT(discord_id) DO UPDATE SET
            discord_name = excluded.discord_name,
            updated_at = CURRENT_TIMESTAMP
    ''', (discord_id, discord_name))

    if game == "lol":
        c.execute('''
            UPDATE users SET lol_username = ?, lol_tag = ?, updated_at = CURRENT_TIMESTAMP
            WHERE discord_id = ?
        ''', (kwargs["username"], kwargs["tag"], discord_id))
    elif game == "tft":
        c.execute('''
            UPDATE users SET tft_username = ?, tft_tag = ?, updated_at = CURRENT_TIMESTAMP
            WHERE discord_id = ?
        ''', (kwargs["username"], kwargs["tag"], discord_id))
    elif game == "valorant":
        c.execute('''
            UPDATE users SET valorant_username = ?, valorant_tag = ?, updated_at = CURRENT_TIMESTAMP
            WHERE discord_id = ?
        ''', (kwargs["username"], kwargs["tag"], discord_id))
    elif game == "cs2":
        c.execute('''
            UPDATE users SET steam_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE discord_id = ?
        ''', (kwargs["steam_id"], discord_id))
    elif game == "wow":
        c.execute('''
            UPDATE users SET wow_character = ?, wow_realm = ?, wow_region = ?, updated_at = CURRENT_TIMESTAMP
            WHERE discord_id = ?
        ''', (kwargs["character"], kwargs["realm"], kwargs.get("region", "eu"), discord_id))

    conn.commit()
    conn.close()

def get_user(discord_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE discord_id = ?', (discord_id,))
    row = c.fetchone()
    conn.close()
    if row:
        columns = [d[0] for d in c.description] if c.description else [
            "discord_id", "discord_name", "lol_username", "lol_tag",
            "tft_username", "tft_tag", "valorant_username", "valorant_tag",
            "steam_id", "wow_character", "wow_realm", "wow_region",
            "created_at", "updated_at"
        ]
        return dict(zip(columns, row))
    return None

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_user(discord_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE discord_id = ?', (discord_id,))
    conn.commit()
    conn.close()