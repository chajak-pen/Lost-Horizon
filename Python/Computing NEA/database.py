import sqlite3
import sys
import os
import hashlib
import binascii
import hmac
import json
from datetime import date

# Default database filename
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "scores_and_times.db")

CASINO_DAILY_CHIP_BONUS = 25
CASINO_BUY_IN_COIN_COST = 12
CASINO_BUY_IN_CHIP_GAIN = 90
TRAINING_TRIAL_REWARD_MAP = {
    'bronze': 15,
    'silver': 30,
    'gold': 50,
}
SHOP_PRICE_INFLATION_STEP_COINS = 150
SHOP_PRICE_INFLATION_RATE = 0.05
SHOP_PRICE_INFLATION_CAP = 1.75
CASINO_VIP_TIERS = [
    {'key': 'guest', 'label': 'Guest Floor', 'required_reputation': 0, 'perk': 'Standard tables and cashier access.'},
    {'key': 'silver', 'label': 'Silver Lounge', 'required_reputation': 25, 'perk': 'Unlocks upgraded prize-counter stock.'},
    {'key': 'gold', 'label': 'Gold Lounge', 'required_reputation': 60, 'perk': 'Unlocks premium high-roller collectibles.'},
    {'key': 'diamond', 'label': 'Diamond Lounge', 'required_reputation': 110, 'perk': 'Signals full casino mastery and VIP status.'},
]


def create_connection(db_file=None):
    #Return a sqlite3 connection to db_file or None on error
    try:
        conn = sqlite3.connect(db_file or DB_FILE)
        return conn
    except sqlite3.Error as e:
        print(f"SQLite connection error: {e}")
        return None


def _is_missing_replay_schema_error(error):
    message = str(error or "").lower()
    if "replay_runs" not in message:
        return False
    replay_fields = ("mini_video_json", "run_outcome", "is_public")
    return any(field in message for field in replay_fields)


def initialize_database(conn=None):
    
    #Create required tables. If conn is None the function opens and
    #closes a temporary connection to the default DB file.
    
    close_after = False
    if conn is None:
        conn = create_connection()
        close_after = True

    if conn is None:
        print("Failed to initialize database: cannot open connection")
        return

    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL UNIQUE,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                coins_collected INTEGER DEFAULT 0,
                casino_chips INTEGER DEFAULT 0,
                casino_reputation INTEGER DEFAULT 0,
                lives INTEGER DEFAULT 3,
                "float" INTEGER DEFAULT 0,
                invincibility INTEGER DEFAULT 0,
                fire INTEGER DEFAULT 0,
                hard_mode_enabled INTEGER DEFAULT 0,
                password_hash TEXT,
                password_salt TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scores (
                score_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                coins_collected INTEGER DEFAULT 0,
                difficulty TEXT DEFAULT 'normal',
                achieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS times (
                time_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                completion_time REAL NOT NULL,
                coins_collected INTEGER DEFAULT 0,
                difficulty TEXT DEFAULT 'normal',
                game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_levels (
                player_id INTEGER NOT NULL,
                level_id INTEGER NOT NULL,
                completed INTEGER DEFAULT 0,
                completion_date TIMESTAMP,
                PRIMARY KEY (player_id, level_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_level_medals (
                player_id INTEGER NOT NULL,
                level_id INTEGER NOT NULL,
                medal TEXT DEFAULT 'none',
                completion_time REAL,
                death_count INTEGER DEFAULT 0,
                coins_collected INTEGER DEFAULT 0,
                coins_total INTEGER DEFAULT 0,
                achieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (player_id, level_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_times_time ON times(completion_time ASC)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS level_deaths (
                player_id INTEGER NOT NULL,
                level_id INTEGER NOT NULL,
                death_count INTEGER DEFAULT 0,
                PRIMARY KEY (player_id, level_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS survival_scores (
                survival_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                waves_survived INTEGER DEFAULT 0,
                achieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_friends (
                player_id INTEGER NOT NULL,
                friend_id INTEGER NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (player_id, friend_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
                FOREIGN KEY (friend_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                level_id INTEGER,
                event_type TEXT NOT NULL,
                x INTEGER,
                y INTEGER,
                meta TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_levels (
                custom_level_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_player_id INTEGER NOT NULL,
                level_name TEXT NOT NULL,
                theme TEXT NOT NULL DEFAULT 'world1',
                config_json TEXT NOT NULL,
                is_finished INTEGER DEFAULT 0,
                is_public INTEGER DEFAULT 0,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_level_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                custom_level_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                completion_time REAL NOT NULL,
                coins_collected INTEGER DEFAULT 0,
                achieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (custom_level_id) REFERENCES custom_levels(custom_level_id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_challenge_runs (
                daily_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_key TEXT NOT NULL,
                level_id INTEGER NOT NULL,
                seed INTEGER NOT NULL,
                challenge_code TEXT NOT NULL,
                player_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                completion_time REAL NOT NULL,
                coins_collected INTEGER DEFAULT 0,
                achieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_meta_upgrades (
                player_id INTEGER PRIMARY KEY,
                mobility_level INTEGER DEFAULT 0,
                survivability_level INTEGER DEFAULT 0,
                economy_level INTEGER DEFAULT 0,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS replay_runs (
                replay_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                level_id INTEGER NOT NULL,
                score INTEGER DEFAULT 0,
                completion_time REAL NOT NULL,
                timeline_json TEXT NOT NULL,
                mini_video_json TEXT,
                run_outcome TEXT DEFAULT 'completed',
                is_public INTEGER DEFAULT 1,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_level_metrics (
                custom_level_id INTEGER PRIMARY KEY,
                plays INTEGER DEFAULT 0,
                clears INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (custom_level_id) REFERENCES custom_levels(custom_level_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_level_likes (
                custom_level_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (custom_level_id, player_id),
                FOREIGN KEY (custom_level_id) REFERENCES custom_levels(custom_level_id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quest_progress (
                player_id INTEGER NOT NULL,
                quest_key TEXT NOT NULL,
                period_key TEXT NOT NULL,
                target_value INTEGER NOT NULL,
                progress_value INTEGER DEFAULT 0,
                reward_coins INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                claimed INTEGER DEFAULT 0,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (player_id, quest_key, period_key),
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_cosmetics (
                player_id INTEGER NOT NULL,
                cosmetic_key TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (player_id, cosmetic_key),
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_prestige (
                player_id INTEGER PRIMARY KEY,
                prestige_level INTEGER DEFAULT 0,
                prestige_points INTEGER DEFAULT 0,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_training_trials (
                player_id INTEGER NOT NULL,
                trial_key TEXT NOT NULL,
                best_medal TEXT DEFAULT 'none',
                best_time REAL,
                best_deaths INTEGER,
                completion_count INTEGER DEFAULT 0,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (player_id, trial_key),
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS casino_stats (
                player_id INTEGER PRIMARY KEY,
                total_chips_wagered INTEGER DEFAULT 0,
                total_chips_paid_out INTEGER DEFAULT 0,
                blackjack_hands INTEGER DEFAULT 0,
                roulette_spins INTEGER DEFAULT 0,
                slot_spins INTEGER DEFAULT 0,
                skillshot_rounds INTEGER DEFAULT 0,
                daily_bonus_claims INTEGER DEFAULT 0,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS casino_daily_claims (
                player_id INTEGER NOT NULL,
                date_key TEXT NOT NULL,
                claim_key TEXT NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (player_id, date_key, claim_key),
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        ''')

        # Add missing columns if they don't exist
        _add_missing_columns(cursor)

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analytics_player_level ON analytics_events(player_id, level_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analytics_type ON analytics_events(event_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_custom_levels_owner ON custom_levels(owner_player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_custom_levels_public ON custom_levels(is_public, is_finished)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_custom_runs_level_score ON custom_level_runs(custom_level_id, score DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_custom_runs_level_time ON custom_level_runs(custom_level_id, completion_time ASC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_runs_date_score ON daily_challenge_runs(date_key, score DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_runs_date_time ON daily_challenge_runs(date_key, completion_time ASC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_meta_upgrades_update ON player_meta_upgrades(updated_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_replay_runs_player_time ON replay_runs(player_id, completion_time ASC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_replay_runs_level_time ON replay_runs(level_id, completion_time ASC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_replay_runs_public_level_time ON replay_runs(is_public, level_id, completion_time ASC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_custom_likes_level ON custom_level_likes(custom_level_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_quest_progress_player_period ON quest_progress(player_id, period_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cosmetics_player ON player_cosmetics(player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_training_trials_player ON player_training_trials(player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_survival_score ON survival_scores(score DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_casino_claims_player_date ON casino_daily_claims(player_id, date_key)')
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database init error: {e}")
    finally:
        if close_after:
            conn.close()


def _add_missing_columns(cursor):
    #Add missing columns to existing tables for schema migration
    try:
        # Check if coins_collected exists in scores table
        cursor.execute("PRAGMA table_info(scores)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'coins_collected' not in columns:
            cursor.execute('ALTER TABLE scores ADD COLUMN coins_collected INTEGER DEFAULT 0')
        
        if 'level' not in columns:
            cursor.execute('ALTER TABLE scores ADD COLUMN level INTEGER DEFAULT 1')

        if 'run_mode' not in columns:
            cursor.execute("ALTER TABLE scores ADD COLUMN run_mode TEXT DEFAULT 'standard'")
        
        # Check if coins_collected exists in times table
        cursor.execute("PRAGMA table_info(times)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'coins_collected' not in columns:
            cursor.execute('ALTER TABLE times ADD COLUMN coins_collected INTEGER DEFAULT 0')
        
        if 'level' not in columns:
            cursor.execute('ALTER TABLE times ADD COLUMN level INTEGER DEFAULT 1')

        if 'run_mode' not in columns:
            cursor.execute("ALTER TABLE times ADD COLUMN run_mode TEXT DEFAULT 'standard'")
        
        # Check if hard_mode_enabled exists in players table
        cursor.execute("PRAGMA table_info(players)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'coins_collected' not in columns:
            cursor.execute('ALTER TABLE players ADD COLUMN coins_collected INTEGER DEFAULT 0')

        if 'casino_chips' not in columns:
            cursor.execute('ALTER TABLE players ADD COLUMN casino_chips INTEGER DEFAULT 0')

        if 'casino_reputation' not in columns:
            cursor.execute('ALTER TABLE players ADD COLUMN casino_reputation INTEGER DEFAULT 0')

        if 'lives' not in columns:
            cursor.execute('ALTER TABLE players ADD COLUMN lives INTEGER DEFAULT 3')

        if 'float' not in columns:
            cursor.execute('ALTER TABLE players ADD COLUMN "float" INTEGER DEFAULT 0')

        if 'invincibility' not in columns:
            cursor.execute('ALTER TABLE players ADD COLUMN invincibility INTEGER DEFAULT 0')

        if 'fire' not in columns:
            cursor.execute('ALTER TABLE players ADD COLUMN fire INTEGER DEFAULT 0')
        
        if 'hard_mode_enabled' not in columns:
            cursor.execute('ALTER TABLE players ADD COLUMN hard_mode_enabled INTEGER DEFAULT 0')

        if 'password_hash' not in columns:
            cursor.execute('ALTER TABLE players ADD COLUMN password_hash TEXT')

        if 'password_salt' not in columns:
            cursor.execute('ALTER TABLE players ADD COLUMN password_salt TEXT')

        # Replay run columns
        cursor.execute("PRAGMA table_info(replay_runs)")
        replay_columns = [col[1] for col in cursor.fetchall()]
        if 'mini_video_json' not in replay_columns:
            cursor.execute('ALTER TABLE replay_runs ADD COLUMN mini_video_json TEXT')
        if 'run_outcome' not in replay_columns:
            cursor.execute("ALTER TABLE replay_runs ADD COLUMN run_outcome TEXT DEFAULT 'completed'")
        if 'is_public' not in replay_columns:
            cursor.execute('ALTER TABLE replay_runs ADD COLUMN is_public INTEGER DEFAULT 1')

        # Skin columns
        for col, defn in [('gold_skin',  'INTEGER DEFAULT 0'),
                          ('shadow_skin', 'INTEGER DEFAULT 0'),
                          ('neon_skin',   'INTEGER DEFAULT 0'),
                          ('active_skin', "TEXT DEFAULT 'default'")]:
            if col not in columns:
                cursor.execute(f'ALTER TABLE players ADD COLUMN {col} {defn}')

        for col, defn in [('ng_plus_unlocked', 'INTEGER DEFAULT 0'),
                          ('ng_plus_enabled', 'INTEGER DEFAULT 0')]:
            if col not in columns:
                cursor.execute(f'ALTER TABLE players ADD COLUMN {col} {defn}')

        for col, defn in [('profile_title', "TEXT DEFAULT 'Rookie Explorer'"),
                          ('profile_badge', "TEXT DEFAULT 'none'"),
                          ('favorite_skin', "TEXT DEFAULT 'default'")]:
            if col not in columns:
                cursor.execute(f'ALTER TABLE players ADD COLUMN {col} {defn}')

        cursor.execute("PRAGMA table_info(casino_stats)")
        casino_columns = [col[1] for col in cursor.fetchall()]
        if 'skillshot_rounds' not in casino_columns:
            cursor.execute('ALTER TABLE casino_stats ADD COLUMN skillshot_rounds INTEGER DEFAULT 0')

    except sqlite3.Error as e:
        print(f"Migration error (non-critical): {e}")


def save_score(conn, player_name, score, coins_collected, level_id, run_mode='standard'):
    #Save a score using an open connection and a player name
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO scores (player_id, score, coins_collected, level, run_mode) VALUES (?, ?, ?, ?, ?)',
            (player_id, score, coins_collected, level_id, (run_mode or 'standard')),
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"save_score error: {e}")
        return False


def save_time(conn, player_name, completion_time, coins_collected, level_id, run_mode='standard'):
    #Save a completion time using an open connection and a player name
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO times (player_id, completion_time, coins_collected, level, run_mode) VALUES (?, ?, ?, ?, ?)',
            (player_id, completion_time, coins_collected, level_id, (run_mode or 'standard')),
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"save_time error: {e}")
        return False
    
def add_total_coins(conn, player_name, coins):
    #add to players total coins collected
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET coins_collected = coins_collected + ? WHERE player_id = ?', (coins, player_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"add_total_coins error: {e}")
        return False
    
def get_total_coins(conn, player_name):
    if conn is None:
        return 0
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT coins_collected FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.Error as e:
        print(f"get_total_coins error: {e}")
        return 0

def subtract_total_coins(conn, player_name, coins):
    #subtract from players total coins collected
    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET coins_collected = coins_collected - ? WHERE player_name = ?', (coins, player_name))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"subtract_total_coins error: {e}")
        return False


def add_total_chips(conn, player_name, chips):
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET casino_chips = casino_chips + ? WHERE player_id = ?', (max(0, int(chips)), player_id))
        conn.commit()
        return True
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"add_total_chips error: {e}")
        return False


def get_total_chips(conn, player_name):
    if conn is None:
        return 0
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT casino_chips FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        return int((row or [0])[0] or 0)
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_total_chips error: {e}")
        return 0


def subtract_total_chips(conn, player_name, chips):
    try:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE players SET casino_chips = MAX(0, casino_chips - ?) WHERE player_name = ?',
            (max(0, int(chips)), player_name),
        )
        conn.commit()
        return True
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"subtract_total_chips error: {e}")
        return False


def _ensure_casino_stats_row(conn, player_id):
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT OR IGNORE INTO casino_stats
        (player_id, total_chips_wagered, total_chips_paid_out, blackjack_hands, roulette_spins, slot_spins, skillshot_rounds, daily_bonus_claims)
        VALUES (?, 0, 0, 0, 0, 0, 0, 0)
        ''',
        (int(player_id),),
    )


def record_casino_play(conn, player_name, game_key, wager, payout):
    if conn is None:
        return False
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        _ensure_casino_stats_row(conn, player_id)
        game_columns = {
            'blackjack': 'blackjack_hands',
            'roulette': 'roulette_spins',
            'slots': 'slot_spins',
            'skillshot': 'skillshot_rounds',
        }
        stat_col = game_columns.get(game_key)
        if stat_col is None:
            return False
        wager = max(0, int(wager))
        payout = max(0, int(payout))
        cursor = conn.cursor()
        cursor.execute(
            f'''
            UPDATE casino_stats
            SET total_chips_wagered = total_chips_wagered + ?,
                total_chips_paid_out = total_chips_paid_out + ?,
                {stat_col} = {stat_col} + 1,
                updated_date = CURRENT_TIMESTAMP
            WHERE player_id = ?
            ''',
            (wager, payout, int(player_id)),
        )
        rep_gain = max(1, wager // 25) if wager > 0 else 0
        if rep_gain:
            cursor.execute(
                'UPDATE players SET casino_reputation = casino_reputation + ? WHERE player_id = ?',
                (rep_gain, int(player_id)),
            )
        conn.commit()
        add_quest_progress(player_name, 'daily_casino_floor', 1, period='daily')
        add_quest_progress(player_name, 'daily_casino_wager', wager, period='daily')
        add_quest_progress(player_name, 'weekly_casino_wager', wager, period='weekly')
        if payout > 0:
            add_quest_progress(player_name, 'weekly_casino_hits', 1, period='weekly')
        return True
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"record_casino_play error: {e}")
        return False


def get_casino_profile(player_name):
    conn = create_connection()
    if conn is None:
        return {
            'chips': 0,
            'reputation': 0,
            'total_wagered': 0,
            'total_paid_out': 0,
            'net': 0,
            'blackjack_hands': 0,
            'roulette_spins': 0,
            'slot_spins': 0,
            'skillshot_rounds': 0,
            'daily_bonus_claims': 0,
        }
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return {
                'chips': 0,
                'reputation': 0,
                'total_wagered': 0,
                'total_paid_out': 0,
                'net': 0,
                'blackjack_hands': 0,
                'roulette_spins': 0,
                'slot_spins': 0,
                'skillshot_rounds': 0,
                'daily_bonus_claims': 0,
            }
        _ensure_casino_stats_row(conn, player_id)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT p.casino_chips, p.casino_reputation,
                   cs.total_chips_wagered, cs.total_chips_paid_out,
                   cs.blackjack_hands, cs.roulette_spins, cs.slot_spins, cs.skillshot_rounds, cs.daily_bonus_claims
            FROM players p
            JOIN casino_stats cs ON cs.player_id = p.player_id
            WHERE p.player_id = ?
            ''',
            (int(player_id),),
        )
        row = cursor.fetchone() or (0, 0, 0, 0, 0, 0, 0, 0, 0)
        return {
            'chips': int(row[0] or 0),
            'reputation': int(row[1] or 0),
            'total_wagered': int(row[2] or 0),
            'total_paid_out': int(row[3] or 0),
            'net': int((row[3] or 0) - (row[2] or 0)),
            'blackjack_hands': int(row[4] or 0),
            'roulette_spins': int(row[5] or 0),
            'slot_spins': int(row[6] or 0),
            'skillshot_rounds': int(row[7] or 0),
            'daily_bonus_claims': int(row[8] or 0),
        }
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_casino_profile error: {e}")
        return {
            'chips': 0,
            'reputation': 0,
            'total_wagered': 0,
            'total_paid_out': 0,
            'net': 0,
            'blackjack_hands': 0,
            'roulette_spins': 0,
            'slot_spins': 0,
            'skillshot_rounds': 0,
            'daily_bonus_claims': 0,
        }
    finally:
        conn.close()


def claim_casino_daily_bonus(player_name, claim_key='cashier_bonus', chips_award=CASINO_DAILY_CHIP_BONUS):
    conn = create_connection()
    if conn is None:
        return False, 'No database connection.'
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False, 'Player not found.'
        _ensure_casino_stats_row(conn, player_id)
        today_key = date.today().isoformat()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT 1 FROM casino_daily_claims WHERE player_id = ? AND date_key = ? AND claim_key = ?',
            (int(player_id), today_key, str(claim_key)),
        )
        if cursor.fetchone():
            return False, 'Daily bonus already claimed.'
        cursor.execute(
            'INSERT INTO casino_daily_claims (player_id, date_key, claim_key) VALUES (?, ?, ?)',
            (int(player_id), today_key, str(claim_key)),
        )
        cursor.execute(
            'UPDATE players SET casino_chips = casino_chips + ?, casino_reputation = casino_reputation + 2 WHERE player_id = ?',
            (max(0, int(chips_award)), int(player_id)),
        )
        cursor.execute(
            '''
            UPDATE casino_stats
            SET daily_bonus_claims = daily_bonus_claims + 1,
                updated_date = CURRENT_TIMESTAMP
            WHERE player_id = ?
            ''',
            (int(player_id),),
        )
        conn.commit()
        return True, f'Cashier bonus claimed: +{int(chips_award)} chips.'
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"claim_casino_daily_bonus error: {e}")
        return False, 'Daily bonus unavailable.'
    finally:
        conn.close()

def get_player_lives(conn, player_name):
    if conn is None:
        return 0
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return 0
        cursor = conn.cursor()
        cursor.execute('SELECT lives FROM players WHERE player_id = ?', (player_id,))
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.Error as e:
        print(f"get_player_lives error: {e}")
        return 0

def add_lives(conn, player_name, lives):
    #add to players total lives
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET lives = lives + ? WHERE player_id = ?', (lives, player_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"add_lives error: {e}")
        return False

def subtract_life(conn, player_name):
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET lives = lives - 1 WHERE player_id = ? AND lives > 0', (player_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"subtract_life error: {e}")
        return False
    
def add_powerup(conn, player_name, powerup, amount=1):
    #add to players powerup count
    try:
        if powerup not in ('float', 'invincibility', 'fire'):
            return False
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute(f'UPDATE players SET "{powerup}" = "{powerup}" + ? WHERE player_id = ?', (amount, player_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"add_powerup error: {e}")
        return False

def get_powerup_count(conn, player_name, powerup):
    if conn is None:
        return 0
    try:
        if powerup not in ('float', 'invincibility', 'fire'):
            return 0
        player_id = add_player(conn, player_name)
        if not player_id:
            return 0
        cursor = conn.cursor()
        cursor.execute(f'SELECT "{powerup}" FROM players WHERE player_id = ?', (player_id,))
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.Error as e:
        print(f"get_powerup_count error: {e}")
        return 0

def remove_powerup(conn, player_name, powerup, amount=1):
    if conn is None:
        return False
    try:
        if powerup not in ('float', 'invincibility', 'fire'):
            return False
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute(f'UPDATE players SET "{powerup}" = "{powerup}" - ? WHERE player_id = ?', (amount, player_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"removing powerup error: {e}")
        return False

def get_high_scores(level_id, limit=10):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.player_name, s.score, COALESCE(s.run_mode, 'standard') FROM scores s
            JOIN players p ON s.player_id = p.player_id
            WHERE s.level = ?
            ORDER BY s.score DESC
            LIMIT ?
        ''', (level_id, limit))
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as e:
        print(f"get_high_scores error: {e}")
        return []
    finally:
        conn.close()


def get_high_scores_global(limit=10, weekly=False):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        q = '''
            SELECT p.player_name, MAX(s.score) AS best_score
            FROM scores s
            JOIN players p ON s.player_id = p.player_id
        '''
        params = []
        if weekly:
            q += " WHERE s.achieved_date >= datetime('now', '-7 days')"
        q += " GROUP BY p.player_id ORDER BY best_score DESC LIMIT ?"
        params.append(limit)
        cursor.execute(q, tuple(params))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"get_high_scores_global error: {e}")
        return []
    finally:
        conn.close()


def get_high_scores_friends(player_name, level_id=None, limit=10, weekly=False):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        if not row:
            return []
        pid = row[0]

        where = ["(s.player_id = ? OR s.player_id IN (SELECT friend_id FROM player_friends WHERE player_id = ?))"]
        params = [pid, pid]
        if level_id is not None:
            where.append("s.level = ?")
            params.append(level_id)
        if weekly:
            where.append("s.achieved_date >= datetime('now', '-7 days')")

        query = f'''
            SELECT p.player_name, MAX(s.score) AS best_score
            FROM scores s
            JOIN players p ON s.player_id = p.player_id
            WHERE {' AND '.join(where)}
            GROUP BY p.player_id
            ORDER BY best_score DESC
            LIMIT ?
        '''
        params.append(limit)
        cursor.execute(query, tuple(params))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"get_high_scores_friends error: {e}")
        return []
    finally:
        conn.close()


def get_fastest_times(level_id, limit=10):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.player_name, t.completion_time, t.coins_collected, COALESCE(t.run_mode, 'standard') FROM times t
            JOIN players p ON t.player_id = p.player_id
            WHERE t.level = ?
            ORDER BY t.completion_time ASC
            LIMIT ?
        ''', (level_id, limit))
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as e:
        print(f"get_fastest_times error: {e}")
        return []
    finally:
        conn.close()


def get_fastest_times_global(limit=10, weekly=False):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        q = '''
            SELECT p.player_name, MIN(t.completion_time) as best_time
            FROM times t
            JOIN players p ON t.player_id = p.player_id
        '''
        if weekly:
            q += " WHERE t.game_date >= datetime('now', '-7 days')"
        q += " GROUP BY p.player_id ORDER BY best_time ASC LIMIT ?"
        cursor.execute(q, (limit,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"get_fastest_times_global error: {e}")
        return []
    finally:
        conn.close()


def get_fastest_times_friends(player_name, level_id=None, limit=10, weekly=False):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        if not row:
            return []
        pid = row[0]

        where = ["(t.player_id = ? OR t.player_id IN (SELECT friend_id FROM player_friends WHERE player_id = ?))"]
        params = [pid, pid]
        if level_id is not None:
            where.append("t.level = ?")
            params.append(level_id)
        if weekly:
            where.append("t.game_date >= datetime('now', '-7 days')")

        query = f'''
            SELECT p.player_name, MIN(t.completion_time) as best_time
            FROM times t
            JOIN players p ON t.player_id = p.player_id
            WHERE {' AND '.join(where)}
            GROUP BY p.player_id
            ORDER BY best_time ASC
            LIMIT ?
        '''
        params.append(limit)
        cursor.execute(query, tuple(params))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"get_fastest_times_friends error: {e}")
        return []
    finally:
        conn.close()


def get_player_best_score(player_name, level_id):
    """Return the player's existing best score for a level, or None if no entry."""
    conn = create_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT MAX(s.score) FROM scores s
            JOIN players p ON s.player_id = p.player_id
            WHERE p.player_name = ? AND s.level = ?
        ''', (player_name, level_id))
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else None
    except sqlite3.Error as e:
        print(f"get_player_best_score error: {e}")
        return None
    finally:
        conn.close()


def get_player_best_time(player_name, level_id):
    """Return the player's existing best completion time for a level, or None if no entry."""
    conn = create_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT MIN(t.completion_time) FROM times t
            JOIN players p ON t.player_id = p.player_id
            WHERE p.player_name = ? AND t.level = ?
        ''', (player_name, level_id))
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else None
    except sqlite3.Error as e:
        print(f"get_player_best_time error: {e}")
        return None
    finally:
        conn.close()


def _medal_rank(medal):
    ranks = {'none': 0, 'bronze': 1, 'silver': 2, 'gold': 3}
    return ranks.get((medal or 'none').lower(), 0)


def save_level_medal(conn, player_name, level_id, medal, completion_time, death_count, coins_collected, coins_total):
    """Persist the player's best medal per level, upgrading only when a higher rank is earned."""
    if conn is None:
        return False
    try:
        normalized = (medal or 'none').lower()
        if normalized not in ('none', 'bronze', 'silver', 'gold'):
            normalized = 'none'

        player_id = add_player(conn, player_name)
        if not player_id:
            return False

        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT medal, completion_time, death_count, coins_collected, coins_total
            FROM player_level_medals
            WHERE player_id = ? AND level_id = ?
            ''',
            (player_id, level_id),
        )
        row = cursor.fetchone()

        if row is None:
            cursor.execute(
                '''
                INSERT INTO player_level_medals
                (player_id, level_id, medal, completion_time, death_count, coins_collected, coins_total, achieved_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                (player_id, level_id, normalized, float(completion_time), int(death_count), int(coins_collected), int(coins_total)),
            )
            conn.commit()
            return True

        old_medal, old_time, old_deaths, old_coins, old_total = row
        old_rank = _medal_rank(old_medal)
        new_rank = _medal_rank(normalized)

        merged_medal = old_medal if old_rank > new_rank else normalized
        merged_time = min(float(old_time) if old_time is not None else float(completion_time), float(completion_time))
        merged_deaths = min(int(old_deaths) if old_deaths is not None else int(death_count), int(death_count))
        merged_coins = max(int(old_coins) if old_coins is not None else int(coins_collected), int(coins_collected))
        merged_total = max(int(old_total) if old_total is not None else int(coins_total), int(coins_total))

        cursor.execute(
            '''
            UPDATE player_level_medals
            SET medal = ?, completion_time = ?, death_count = ?, coins_collected = ?, coins_total = ?, achieved_date = CURRENT_TIMESTAMP
            WHERE player_id = ? AND level_id = ?
            ''',
            (merged_medal, merged_time, merged_deaths, merged_coins, merged_total, player_id, level_id),
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"save_level_medal error: {e}")
        return False


def get_player_level_medal(player_name, level_id):
    conn = create_connection()
    if conn is None:
        return 'none'
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT plm.medal
            FROM player_level_medals plm
            JOIN players p ON p.player_id = plm.player_id
            WHERE p.player_name = ? AND plm.level_id = ?
            ''',
            (player_name, level_id),
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] else 'none'
    except sqlite3.Error as e:
        print(f"get_player_level_medal error: {e}")
        return 'none'
    finally:
        conn.close()


def get_player_death_count(player_name, level_id):
    conn = create_connection()
    if conn is None:
        return 0
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        if not row:
            return 0
        player_id = row[0]
        cursor.execute('SELECT death_count FROM level_deaths WHERE player_id = ? AND level_id = ?',
                       (player_id, level_id))
        dead_row = cursor.fetchone()
        return dead_row[0] if dead_row else 0
    except sqlite3.Error as e:
        print(f"get_player_death_count error: {e}")
        return 0
    finally:
        conn.close()


def increment_level_death(player_name, level_id):
    conn = create_connection()
    if conn is None:
        return
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        if not row:
            return
        player_id = row[0]
        cursor.execute('''
            INSERT INTO level_deaths (player_id, level_id, death_count) VALUES (?, ?, 1)
            ON CONFLICT(player_id, level_id) DO UPDATE SET death_count = death_count + 1
        ''', (player_id, level_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"increment_level_death error: {e}")
    finally:
        conn.close()


def get_player_skin(player_name):
    conn = create_connection()
    if conn is None:
        return 'default'
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT active_skin FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else 'default'
    except sqlite3.Error as e:
        print(f"get_player_skin error: {e}")
        return 'default'
    finally:
        conn.close()


def set_player_skin(player_name, skin_key):
    conn = create_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET active_skin = ? WHERE player_name = ?', (skin_key, player_name))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"set_player_skin error: {e}")
        return False
    finally:
        conn.close()


def get_owned_skins(player_name):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT gold_skin, shadow_skin, neon_skin FROM players WHERE player_name = ?',
                       (player_name,))
        row = cursor.fetchone()
        if not row:
            return []
        owned = []
        if row[0]: owned.append('gold')
        if row[1]: owned.append('shadow')
        if row[2]: owned.append('neon')
        return owned
    except sqlite3.Error as e:
        print(f"get_owned_skins error: {e}")
        return []
    finally:
        conn.close()


def buy_skin(conn, player_name, skin_key):
    try:
        cursor = conn.cursor()
        col = f"{skin_key}_skin"
        cursor.execute(f'UPDATE players SET "{col}" = 1, active_skin = ? WHERE player_name = ?',
                       (skin_key, player_name))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"buy_skin error: {e}")
        return False


def is_ng_plus_unlocked(player_name):
    conn = create_connection()
    if conn is None:
        return False
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute('SELECT ng_plus_unlocked FROM players WHERE player_id = ?', (player_id,))
        row = cursor.fetchone()
        return bool(row and row[0])
    except sqlite3.Error as e:
        print(f"is_ng_plus_unlocked error: {e}")
        return False
    finally:
        conn.close()


def is_ng_plus_enabled(player_name):
    conn = create_connection()
    if conn is None:
        return False
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute('SELECT ng_plus_enabled FROM players WHERE player_id = ?', (player_id,))
        row = cursor.fetchone()
        return bool(row and row[0])
    except sqlite3.Error as e:
        print(f"is_ng_plus_enabled error: {e}")
        return False
    finally:
        conn.close()


def set_ng_plus_enabled(conn, player_name, enabled):
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE players SET ng_plus_enabled = ? WHERE player_id = ?',
            (1 if enabled else 0, player_id)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"set_ng_plus_enabled error: {e}")
        return False


def unlock_ng_plus(conn, player_name):
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE players SET ng_plus_unlocked = 1 WHERE player_id = ?',
            (player_id,)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"unlock_ng_plus error: {e}")
        return False


def save_survival_score(player_name, score, waves_survived):
    conn = create_connection()
    if conn is None:
        return False
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO survival_scores (player_id, score, waves_survived) VALUES (?, ?, ?)',
            (player_id, int(score), int(waves_survived))
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"save_survival_score error: {e}")
        return False
    finally:
        conn.close()


def get_survival_high_scores(limit=10):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.player_name, s.score, s.waves_survived
            FROM survival_scores s
            JOIN players p ON s.player_id = p.player_id
            ORDER BY s.score DESC, s.waves_survived DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"get_survival_high_scores error: {e}")
        return []
    finally:
        conn.close()


def get_survival_high_scores_friends(player_name, limit=10, weekly=False):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        if not row:
            return []
        pid = row[0]

        where = ["(s.player_id = ? OR s.player_id IN (SELECT friend_id FROM player_friends WHERE player_id = ?))"]
        params = [pid, pid]
        if weekly:
            where.append("s.achieved_date >= datetime('now', '-7 days')")

        query = f'''
            SELECT p.player_name, s.score, s.waves_survived
            FROM survival_scores s
            JOIN players p ON s.player_id = p.player_id
            WHERE {' AND '.join(where)}
            ORDER BY s.score DESC, s.waves_survived DESC
            LIMIT ?
        '''
        params.append(limit)
        cursor.execute(query, tuple(params))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"get_survival_high_scores_friends error: {e}")
        return []
    finally:
        conn.close()


def save_custom_level(conn, player_name, level_name, theme, config_dict, is_finished=False, is_public=False, custom_level_id=None):
    """Insert or update a custom sandbox level and return its ID."""
    if conn is None:
        return None
    try:
        owner_id = add_player(conn, player_name)
        if not owner_id:
            return None

        payload = json.dumps(config_dict or {}, separators=(",", ":"))
        cursor = conn.cursor()
        if custom_level_id is None:
            cursor.execute(
                '''
                INSERT INTO custom_levels
                (owner_player_id, level_name, theme, config_json, is_finished, is_public)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    owner_id,
                    (level_name or 'Sandbox Level').strip()[:64],
                    (theme or 'world1').strip().lower(),
                    payload,
                    1 if is_finished else 0,
                    1 if is_public else 0,
                ),
            )
            new_id = cursor.lastrowid
            conn.commit()
            return new_id

        cursor.execute(
            '''
            UPDATE custom_levels
            SET level_name = ?,
                theme = ?,
                config_json = ?,
                is_finished = ?,
                is_public = ?,
                updated_date = CURRENT_TIMESTAMP
            WHERE custom_level_id = ? AND owner_player_id = ?
            ''',
            (
                (level_name or 'Sandbox Level').strip()[:64],
                (theme or 'world1').strip().lower(),
                payload,
                1 if is_finished else 0,
                1 if is_public else 0,
                int(custom_level_id),
                owner_id,
            ),
        )
        conn.commit()
        return int(custom_level_id) if cursor.rowcount > 0 else None
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"save_custom_level error: {e}")
        return None


def _row_to_custom_level_dict(row):
    if not row:
        return None
    (lvl_id, owner_name, level_name, theme, config_json, is_finished, is_public, created_date, updated_date) = row
    try:
        cfg = json.loads(config_json) if config_json else {}
    except Exception:
        cfg = {}
    return {
        'custom_level_id': int(lvl_id),
        'owner_name': owner_name,
        'level_name': level_name,
        'theme': theme,
        'config': cfg,
        'is_finished': bool(is_finished),
        'is_public': bool(is_public),
        'created_date': created_date,
        'updated_date': updated_date,
    }


def get_custom_level(custom_level_id, requester_name=None):
    conn = create_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT cl.custom_level_id, p.player_name, cl.level_name, cl.theme,
                   cl.config_json, cl.is_finished, cl.is_public, cl.created_date, cl.updated_date
            FROM custom_levels cl
            JOIN players p ON p.player_id = cl.owner_player_id
            WHERE cl.custom_level_id = ?
            ''',
            (int(custom_level_id),),
        )
        row = cursor.fetchone()
        lvl = _row_to_custom_level_dict(row)
        if lvl is None:
            return None
        if lvl['is_public'] or (requester_name and requester_name == lvl['owner_name']):
            return lvl
        return None
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_custom_level error: {e}")
        return None
    finally:
        conn.close()


def list_my_custom_levels(player_name):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT cl.custom_level_id, p.player_name, cl.level_name, cl.theme,
                   cl.config_json, cl.is_finished, cl.is_public, cl.created_date, cl.updated_date
            FROM custom_levels cl
            JOIN players p ON p.player_id = cl.owner_player_id
            WHERE p.player_name = ?
            ORDER BY cl.updated_date DESC, cl.custom_level_id DESC
            ''',
            (player_name,),
        )
        return [_row_to_custom_level_dict(r) for r in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"list_my_custom_levels error: {e}")
        return []
    finally:
        conn.close()


def list_public_custom_levels(limit=100):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT cl.custom_level_id, p.player_name, cl.level_name, cl.theme,
                   cl.config_json, cl.is_finished, cl.is_public, cl.created_date, cl.updated_date
            FROM custom_levels cl
            JOIN players p ON p.player_id = cl.owner_player_id
            WHERE cl.is_public = 1 AND cl.is_finished = 1
            ORDER BY cl.updated_date DESC, cl.custom_level_id DESC
            LIMIT ?
            ''',
            (int(limit),),
        )
        return [_row_to_custom_level_dict(r) for r in cursor.fetchall()]
    except (sqlite3.Error, ValueError) as e:
        print(f"list_public_custom_levels error: {e}")
        return []
    finally:
        conn.close()


def save_custom_level_run(player_name, custom_level_id, score, completion_time, coins_collected=0):
    conn = create_connection()
    if conn is None:
        return False
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False

        cursor = conn.cursor()
        cursor.execute(
            'SELECT 1 FROM custom_levels WHERE custom_level_id = ? AND is_finished = 1',
            (int(custom_level_id),),
        )
        if cursor.fetchone() is None:
            return False

        cursor.execute(
            '''
            INSERT INTO custom_level_runs (custom_level_id, player_id, score, completion_time, coins_collected)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (int(custom_level_id), player_id, int(score), float(completion_time), int(coins_collected)),
        )

        _ensure_custom_level_metrics_row(conn, int(custom_level_id))
        cursor.execute(
            '''
            UPDATE custom_level_metrics
            SET plays = plays + 1,
                clears = clears + 1,
                updated_date = CURRENT_TIMESTAMP
            WHERE custom_level_id = ?
            ''',
            (int(custom_level_id),),
        )
        conn.commit()
        return True
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"save_custom_level_run error: {e}")
        return False
    finally:
        conn.close()


def get_custom_level_top_scores(custom_level_id, limit=10):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT p.player_name, MAX(r.score) AS best_score
            FROM custom_level_runs r
            JOIN players p ON p.player_id = r.player_id
            WHERE r.custom_level_id = ?
            GROUP BY r.player_id
            ORDER BY best_score DESC
            LIMIT ?
            ''',
            (int(custom_level_id), int(limit)),
        )
        return cursor.fetchall()
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_custom_level_top_scores error: {e}")
        return []
    finally:
        conn.close()


def get_custom_level_top_times(custom_level_id, limit=10):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT p.player_name, MIN(r.completion_time) AS best_time
            FROM custom_level_runs r
            JOIN players p ON p.player_id = r.player_id
            WHERE r.custom_level_id = ?
            GROUP BY r.player_id
            ORDER BY best_time ASC
            LIMIT ?
            ''',
            (int(custom_level_id), int(limit)),
        )
        return cursor.fetchall()
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_custom_level_top_times error: {e}")
        return []
    finally:
        conn.close()


def get_custom_level_player_best_score(player_name, custom_level_id):
    conn = create_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT MAX(r.score)
            FROM custom_level_runs r
            JOIN players p ON p.player_id = r.player_id
            WHERE p.player_name = ? AND r.custom_level_id = ?
            ''',
            (player_name, int(custom_level_id)),
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else None
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_custom_level_player_best_score error: {e}")
        return None
    finally:
        conn.close()


def get_custom_level_player_best_time(player_name, custom_level_id):
    conn = create_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT MIN(r.completion_time)
            FROM custom_level_runs r
            JOIN players p ON p.player_id = r.player_id
            WHERE p.player_name = ? AND r.custom_level_id = ?
            ''',
            (player_name, int(custom_level_id)),
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else None
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_custom_level_player_best_time error: {e}")
        return None
    finally:
        conn.close()


def _ensure_custom_level_metrics_row(conn, custom_level_id):
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT OR IGNORE INTO custom_level_metrics (custom_level_id, plays, clears, likes)
        VALUES (?, 0, 0, 0)
        ''',
        (int(custom_level_id),),
    )


def validate_custom_level_config(config_dict):
    cfg = config_dict or {}
    issues = []
    platforms = list(cfg.get('platforms', []))
    finish = cfg.get('finish_line') or {}
    ww = int(cfg.get('world_width', 0) or 0)
    if ww < 1800:
        issues.append("World width must be at least 1800.")
    if not platforms:
        issues.append("Add at least one platform.")
    if not isinstance(finish, dict):
        issues.append("Finish line is missing.")
    fx = int(finish.get('x', -1) or -1)
    fy = int(finish.get('y', -1) or -1)
    if fx < 0 or fy < 0:
        issues.append("Finish line position is invalid.")
    if platforms:
        nearest_start = min(abs(int(p[0]) - 0) for p in platforms)
        if nearest_start > 280:
            issues.append("Add a start platform near x=0.")
        if fx >= 0:
            nearest_finish = min(abs(int(p[0]) - fx) for p in platforms)
            if nearest_finish > 420:
                issues.append("Add traversable platforms near the finish line.")
    return (len(issues) == 0), issues


def like_custom_level(player_name, custom_level_id):
    conn = create_connection()
    if conn is None:
        return False
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        _ensure_custom_level_metrics_row(conn, custom_level_id)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT OR IGNORE INTO custom_level_likes (custom_level_id, player_id)
            VALUES (?, ?)
            ''',
            (int(custom_level_id), int(player_id)),
        )
        inserted = cursor.rowcount > 0
        if inserted:
            cursor.execute(
                '''
                UPDATE custom_level_metrics
                SET likes = likes + 1,
                    updated_date = CURRENT_TIMESTAMP
                WHERE custom_level_id = ?
                ''',
                (int(custom_level_id),),
            )
        conn.commit()
        return True
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"like_custom_level error: {e}")
        return False
    finally:
        conn.close()


def unlike_custom_level(player_name, custom_level_id):
    conn = create_connection()
    if conn is None:
        return False
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        _ensure_custom_level_metrics_row(conn, custom_level_id)
        cursor = conn.cursor()
        cursor.execute(
            '''
            DELETE FROM custom_level_likes
            WHERE custom_level_id = ? AND player_id = ?
            ''',
            (int(custom_level_id), int(player_id)),
        )
        deleted = cursor.rowcount > 0
        if deleted:
            cursor.execute(
                '''
                UPDATE custom_level_metrics
                SET likes = MAX(0, likes - 1),
                    updated_date = CURRENT_TIMESTAMP
                WHERE custom_level_id = ?
                ''',
                (int(custom_level_id),),
            )
        conn.commit()
        return True
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"unlike_custom_level error: {e}")
        return False
    finally:
        conn.close()


def get_custom_level_metrics(custom_level_id):
    conn = create_connection()
    if conn is None:
        return {'plays': 0, 'clears': 0, 'likes': 0}
    try:
        _ensure_custom_level_metrics_row(conn, custom_level_id)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT plays, clears, likes FROM custom_level_metrics WHERE custom_level_id = ?',
            (int(custom_level_id),),
        )
        row = cursor.fetchone()
        conn.commit()
        if not row:
            return {'plays': 0, 'clears': 0, 'likes': 0}
        return {'plays': int(row[0]), 'clears': int(row[1]), 'likes': int(row[2])}
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_custom_level_metrics error: {e}")
        return {'plays': 0, 'clears': 0, 'likes': 0}
    finally:
        conn.close()


def get_creator_profile_metrics(player_name):
    conn = create_connection()
    if conn is None:
        return {'levels': 0, 'plays': 0, 'clears': 0, 'likes': 0}
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        if not row:
            return {'levels': 0, 'plays': 0, 'clears': 0, 'likes': 0}
        pid = int(row[0])

        cursor.execute('SELECT COUNT(*) FROM custom_levels WHERE owner_player_id = ?', (pid,))
        levels = int(cursor.fetchone()[0] or 0)
        cursor.execute(
            '''
            SELECT COALESCE(SUM(m.plays), 0), COALESCE(SUM(m.clears), 0), COALESCE(SUM(m.likes), 0)
            FROM custom_levels l
            LEFT JOIN custom_level_metrics m ON m.custom_level_id = l.custom_level_id
            WHERE l.owner_player_id = ?
            ''',
            (pid,),
        )
        sum_row = cursor.fetchone() or (0, 0, 0)
        return {
            'levels': levels,
            'plays': int(sum_row[0] or 0),
            'clears': int(sum_row[1] or 0),
            'likes': int(sum_row[2] or 0),
        }
    except sqlite3.Error as e:
        print(f"get_creator_profile_metrics error: {e}")
        return {'levels': 0, 'plays': 0, 'clears': 0, 'likes': 0}
    finally:
        conn.close()


def save_replay_timeline(player_name, level_id, completion_time, score, timeline_frames, is_public=True, run_outcome='completed', mini_video_frames=None, _schema_retry=True):
    conn = create_connection()
    if conn is None:
        return None
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return None
        payload = json.dumps(list(timeline_frames or []), separators=(",", ":"))
        clip_payload = None
        if mini_video_frames:
            clip_payload = json.dumps(list(mini_video_frames), separators=(",", ":"))
        cursor = conn.cursor()
        insert_values = (
            int(player_id),
            int(level_id),
            int(score),
            float(completion_time),
            payload,
            clip_payload,
            str(run_outcome or 'completed'),
            1 if bool(is_public) else 0,
        )
        try:
            cursor.execute(
                '''
                INSERT INTO replay_runs (player_id, level_id, score, completion_time, timeline_json, mini_video_json, run_outcome, is_public)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                insert_values,
            )
        except sqlite3.Error:
            cursor.execute(
                '''
                INSERT INTO replay_runs (player_id, level_id, score, completion_time, timeline_json, mini_video_json, run_outcome, is_public)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    int(player_id),
                    int(level_id),
                    int(score),
                    float(completion_time),
                    payload,
                    None,
                    str(run_outcome or 'completed'),
                    1 if bool(is_public) else 0,
                ),
            )
        conn.commit()
        return int(cursor.lastrowid)
    except (sqlite3.Error, TypeError, ValueError) as e:
        if _schema_retry and _is_missing_replay_schema_error(e):
            initialize_database()
            return save_replay_timeline(player_name, level_id, completion_time, score, timeline_frames, is_public=is_public, run_outcome=run_outcome, mini_video_frames=mini_video_frames, _schema_retry=False)
        print(f"save_replay_timeline error: {e}")
        return None
    finally:
        conn.close()


def list_replay_runs(player_name=None, limit=40, include_private=False, _schema_retry=True):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        if player_name:
            filter_private = "" if include_private else " AND r.is_public = 1 "
            cursor.execute(
                f'''
                SELECT r.replay_id, p.player_name, r.level_id, r.score, r.completion_time, r.created_date, r.run_outcome, r.is_public
                FROM replay_runs r
                JOIN players p ON p.player_id = r.player_id
                WHERE p.player_name = ?
                {filter_private}
                ORDER BY r.created_date DESC
                LIMIT ?
                ''',
                (player_name, int(limit)),
            )
        else:
            cursor.execute(
                '''
                SELECT r.replay_id, p.player_name, r.level_id, r.score, r.completion_time, r.created_date, r.run_outcome, r.is_public
                FROM replay_runs r
                JOIN players p ON p.player_id = r.player_id
                WHERE r.is_public = 1
                ORDER BY r.created_date DESC
                LIMIT ?
                ''',
                (int(limit),),
            )
        rows = cursor.fetchall()
        out = []
        for rr in rows:
            out.append({
                'replay_id': int(rr[0]),
                'player_name': rr[1],
                'level_id': int(rr[2]),
                'score': int(rr[3] or 0),
                'completion_time': float(rr[4]),
                'created_date': rr[5],
                'run_outcome': rr[6] or 'completed',
                'is_public': bool(rr[7]),
            })
        return out
    except (sqlite3.Error, ValueError, TypeError) as e:
        if _schema_retry and _is_missing_replay_schema_error(e):
            initialize_database()
            return list_replay_runs(player_name, limit=limit, include_private=include_private, _schema_retry=False)
        print(f"list_replay_runs error: {e}")
        return []
    finally:
        conn.close()


def get_replay_timeline(replay_id, _schema_retry=True):
    conn = create_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT r.replay_id, p.player_name, r.level_id, r.score, r.completion_time, r.timeline_json, r.created_date,
                   r.mini_video_json, r.run_outcome, r.is_public
            FROM replay_runs r
            JOIN players p ON p.player_id = r.player_id
            WHERE r.replay_id = ?
            ''',
            (int(replay_id),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        try:
            frames = json.loads(row[5]) if row[5] else []
        except Exception:
            frames = []
        try:
            mini_video_frames = json.loads(row[7]) if row[7] else []
        except Exception:
            mini_video_frames = []
        return {
            'replay_id': int(row[0]),
            'player_name': row[1],
            'level_id': int(row[2]),
            'score': int(row[3] or 0),
            'completion_time': float(row[4]),
            'frames': frames,
            'created_date': row[6],
            'mini_video_frames': mini_video_frames,
            'run_outcome': row[8] or 'completed',
            'is_public': bool(row[9]),
        }
    except (sqlite3.Error, ValueError, TypeError) as e:
        if _schema_retry and _is_missing_replay_schema_error(e):
            initialize_database()
            return get_replay_timeline(replay_id, _schema_retry=False)
        print(f"get_replay_timeline error: {e}")
        return None
    finally:
        conn.close()


def list_level_replay_runs(level_id, limit=40, viewer_player_name=None, _schema_retry=True):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        if viewer_player_name:
            cursor.execute(
                '''
                SELECT r.replay_id, p.player_name, r.level_id, r.score, r.completion_time, r.created_date, r.run_outcome, r.is_public
                FROM replay_runs r
                JOIN players p ON p.player_id = r.player_id
                WHERE r.level_id = ? AND (r.is_public = 1 OR p.player_name = ?)
                ORDER BY r.completion_time ASC, r.created_date ASC
                LIMIT ?
                ''',
                (int(level_id), str(viewer_player_name), int(limit)),
            )
        else:
            cursor.execute(
                '''
                SELECT r.replay_id, p.player_name, r.level_id, r.score, r.completion_time, r.created_date, r.run_outcome, r.is_public
                FROM replay_runs r
                JOIN players p ON p.player_id = r.player_id
                WHERE r.level_id = ? AND r.is_public = 1
                ORDER BY r.completion_time ASC, r.created_date ASC
                LIMIT ?
                ''',
                (int(level_id), int(limit)),
            )
        rows = cursor.fetchall()
        out = []
        for rr in rows:
            out.append({
                'replay_id': int(rr[0]),
                'player_name': rr[1],
                'level_id': int(rr[2]),
                'score': int(rr[3] or 0),
                'completion_time': float(rr[4]),
                'created_date': rr[5],
                'run_outcome': rr[6] or 'completed',
                'is_public': bool(rr[7]),
            })
        return out
    except (sqlite3.Error, ValueError, TypeError) as e:
        if _schema_retry and _is_missing_replay_schema_error(e):
            initialize_database()
            return list_level_replay_runs(level_id, limit=limit, viewer_player_name=viewer_player_name, _schema_retry=False)
        print(f"list_level_replay_runs error: {e}")
        return []
    finally:
        conn.close()


def get_best_replay_for_level(level_id, exclude_player_name=None, _schema_retry=True):
    conn = create_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        if exclude_player_name:
            cursor.execute(
                '''
                SELECT r.replay_id
                FROM replay_runs r
                JOIN players p ON p.player_id = r.player_id
                WHERE r.level_id = ? AND r.is_public = 1 AND p.player_name <> ?
                ORDER BY r.completion_time ASC, r.created_date ASC
                LIMIT 1
                ''',
                (int(level_id), str(exclude_player_name)),
            )
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    '''
                    SELECT replay_id
                    FROM replay_runs
                    WHERE level_id = ? AND is_public = 1
                    ORDER BY completion_time ASC, created_date ASC
                    LIMIT 1
                    ''',
                    (int(level_id),),
                )
                row = cursor.fetchone()
        else:
            cursor.execute(
                '''
                SELECT replay_id
                FROM replay_runs
                WHERE level_id = ? AND is_public = 1
                ORDER BY completion_time ASC, created_date ASC
                LIMIT 1
                ''',
                (int(level_id),),
            )
            row = cursor.fetchone()
        if not row:
            return None
        return get_replay_timeline(int(row[0]))
    except (sqlite3.Error, ValueError, TypeError) as e:
        if _schema_retry and _is_missing_replay_schema_error(e):
            initialize_database()
            return get_best_replay_for_level(level_id, exclude_player_name=exclude_player_name, _schema_retry=False)
        print(f"get_best_replay_for_level error: {e}")
        return None
    finally:
        conn.close()


_QUEST_BLUEPRINTS = {
    'daily': [
        {'quest_key': 'daily_coin_hunter', 'target': 140, 'reward': 65, 'label': 'Collect 140 coins', 'category': 'core'},
        {'quest_key': 'daily_combo_chain', 'target': 4, 'reward': 55, 'label': 'Finish 4 combo chains', 'category': 'core'},
        {'quest_key': 'daily_clear_run', 'target': 1, 'reward': 85, 'label': 'Clear 1 level', 'category': 'core'},
        {'quest_key': 'daily_casino_floor', 'target': 3, 'reward': 40, 'label': 'Play 3 casino rounds', 'category': 'casino'},
        {'quest_key': 'daily_casino_wager', 'target': 90, 'reward': 50, 'label': 'Wager 90 chips', 'category': 'casino'},
    ],
    'weekly': [
        {'quest_key': 'weekly_clear_master', 'target': 8, 'reward': 360, 'label': 'Clear 8 levels', 'category': 'core'},
        {'quest_key': 'weekly_style_rank', 'target': 5, 'reward': 280, 'label': 'Earn 5 high style ranks', 'category': 'core'},
        {'quest_key': 'weekly_casino_wager', 'target': 360, 'reward': 160, 'label': 'Wager 360 chips', 'category': 'casino'},
        {'quest_key': 'weekly_casino_hits', 'target': 5, 'reward': 175, 'label': 'Hit 5 casino payouts', 'category': 'casino'},
    ],
}


def _humanize_quest_key(quest_key):
    return str(quest_key or '').replace('_', ' ').strip().title()


def get_quest_definition(quest_key, period=None):
    quest_key = str(quest_key or '')
    periods = [period] if period in _QUEST_BLUEPRINTS else list(_QUEST_BLUEPRINTS.keys())
    for period_name in periods:
        for quest in _QUEST_BLUEPRINTS.get(period_name, []):
            if str(quest.get('quest_key')) == quest_key:
                return {
                    'quest_key': quest_key,
                    'label': str(quest.get('label') or _humanize_quest_key(quest_key)),
                    'category': str(quest.get('category') or 'core'),
                    'period': period_name,
                }
    return {
        'quest_key': quest_key,
        'label': _humanize_quest_key(quest_key),
        'category': 'core',
        'period': period or 'daily',
    }


def get_casino_vip_status(player_name=None, reputation=None):
    resolved_reputation = reputation
    if resolved_reputation is None and player_name:
        resolved_reputation = get_casino_profile(player_name).get('reputation', 0)
    resolved_reputation = max(0, int(resolved_reputation or 0))

    current_tier = CASINO_VIP_TIERS[0]
    next_tier = None
    for tier in CASINO_VIP_TIERS:
        if resolved_reputation >= int(tier['required_reputation']):
            current_tier = tier
        elif next_tier is None:
            next_tier = tier
            break

    return {
        'reputation': resolved_reputation,
        'tier_key': str(current_tier['key']),
        'tier_label': str(current_tier['label']),
        'tier_perk': str(current_tier['perk']),
        'next_tier_key': None if next_tier is None else str(next_tier['key']),
        'next_tier_label': None if next_tier is None else str(next_tier['label']),
        'next_required_reputation': None if next_tier is None else int(next_tier['required_reputation']),
        'reputation_to_next': 0 if next_tier is None else max(0, int(next_tier['required_reputation']) - resolved_reputation),
    }


def _quest_period_key(period):
    from datetime import datetime
    now = datetime.utcnow()
    if period == 'weekly':
        iso = now.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return now.strftime('%Y-%m-%d')


def _ensure_quests_for_period(conn, player_id, period):
    period_key = _quest_period_key(period)
    cursor = conn.cursor()
    for q in _QUEST_BLUEPRINTS.get(period, []):
        cursor.execute(
            '''
            INSERT OR IGNORE INTO quest_progress
            (player_id, quest_key, period_key, target_value, progress_value, reward_coins, completed, claimed)
            VALUES (?, ?, ?, ?, 0, ?, 0, 0)
            ''',
            (int(player_id), q['quest_key'], period_key, int(q['target']), int(q['reward'])),
        )
    return period_key


def get_player_quests(player_name, period='daily'):
    conn = create_connection()
    if conn is None:
        return []
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return []
        period_key = _ensure_quests_for_period(conn, player_id, period)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT quest_key, target_value, progress_value, reward_coins, completed, claimed
            FROM quest_progress
            WHERE player_id = ? AND period_key = ?
            ORDER BY quest_key
            ''',
            (int(player_id), period_key),
        )
        rows = cursor.fetchall()
        conn.commit()
        return [
            {
                'period': period,
                'period_key': period_key,
                'quest_key': r[0],
                'label': get_quest_definition(r[0], period).get('label'),
                'category': get_quest_definition(r[0], period).get('category'),
                'target': int(r[1] or 0),
                'progress': int(r[2] or 0),
                'reward': int(r[3] or 0),
                'completed': bool(r[4]),
                'claimed': bool(r[5]),
            }
            for r in rows
        ]
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_player_quests error: {e}")
        return []
    finally:
        conn.close()


def add_quest_progress(player_name, quest_key, amount, period='daily'):
    conn = create_connection()
    if conn is None:
        return False
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        period_key = _ensure_quests_for_period(conn, player_id, period)
        cursor = conn.cursor()
        cursor.execute(
            '''
            UPDATE quest_progress
            SET progress_value = MIN(target_value, progress_value + ?),
                completed = CASE WHEN progress_value + ? >= target_value THEN 1 ELSE completed END,
                updated_date = CURRENT_TIMESTAMP
            WHERE player_id = ? AND period_key = ? AND quest_key = ?
            ''',
            (int(amount), int(amount), int(player_id), period_key, str(quest_key)),
        )
        conn.commit()
        return cursor.rowcount > 0
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"add_quest_progress error: {e}")
        return False
    finally:
        conn.close()


def claim_quest_reward(player_name, quest_key, period='daily'):
    conn = create_connection()
    if conn is None:
        return False, "No database connection."
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False, "Player not found."
        period_key = _ensure_quests_for_period(conn, player_id, period)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT reward_coins, completed, claimed
            FROM quest_progress
            WHERE player_id = ? AND period_key = ? AND quest_key = ?
            ''',
            (int(player_id), period_key, str(quest_key)),
        )
        row = cursor.fetchone()
        if not row:
            return False, "Quest not found."
        reward, completed, claimed = int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)
        if not completed:
            return False, "Quest not complete yet."
        if claimed:
            return False, "Reward already claimed."
        add_total_coins(conn, player_name, reward)
        cursor.execute(
            '''
            UPDATE quest_progress
            SET claimed = 1,
                updated_date = CURRENT_TIMESTAMP
            WHERE player_id = ? AND period_key = ? AND quest_key = ?
            ''',
            (int(player_id), period_key, str(quest_key)),
        )
        conn.commit()
        return True, f"Claimed {reward} coins."
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"claim_quest_reward error: {e}")
        return False, "Claim failed."
    finally:
        conn.close()


CRAFTING_RECIPES = {
    'aether_cloak': {'cost': 350, 'yield': 'cloak_aether'},
    'ember_trail': {'cost': 420, 'yield': 'trail_ember'},
    'rift_helm': {'cost': 560, 'yield': 'helm_rift'},
}

CASINO_REWARD_SHOP = {
    'vip_lounge_pass': {
        'cost': 120,
        'yield': 'casino_vip_lounge_pass',
        'label': 'VIP Lounge Pass',
        'description': 'Unlocks a prestige collectible tied to the casino wing.',
        'required_reputation': 0,
    },
    'lucky_trail': {
        'cost': 180,
        'yield': 'casino_lucky_trail',
        'label': 'Lucky Trail',
        'description': 'A cosmetic reward for repeat casino visitors.',
        'required_reputation': 25,
    },
    'high_roller_banner': {
        'cost': 280,
        'yield': 'casino_high_roller_banner',
        'label': 'High Roller Banner',
        'description': 'A premium profile-side collectible earned with chips.',
        'required_reputation': 60,
    },
}


def get_player_cosmetics(player_name):
    conn = create_connection()
    if conn is None:
        return {}
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return {}
        cursor = conn.cursor()
        cursor.execute(
            'SELECT cosmetic_key, quantity FROM player_cosmetics WHERE player_id = ?',
            (int(player_id),),
        )
        return {row[0]: int(row[1] or 0) for row in cursor.fetchall()}
    except sqlite3.Error as e:
        print(f"get_player_cosmetics error: {e}")
        return {}
    finally:
        conn.close()


def craft_cosmetic(player_name, recipe_key):
    recipe = CRAFTING_RECIPES.get(recipe_key)
    if recipe is None:
        return False, "Unknown recipe."
    conn = create_connection()
    if conn is None:
        return False, "No database connection."
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False, "Player not found."
        cost = int(recipe.get('cost', 0))
        total = get_total_coins(conn, player_name)
        if total < cost:
            return False, f"Need {cost} coins (have {total})."
        subtract_total_coins(conn, player_name, cost)
        cursor = conn.cursor()
        cosmetic_key = str(recipe.get('yield', recipe_key))
        cursor.execute(
            '''
            INSERT INTO player_cosmetics (player_id, cosmetic_key, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(player_id, cosmetic_key)
            DO UPDATE SET quantity = quantity + 1, updated_date = CURRENT_TIMESTAMP
            ''',
            (int(player_id), cosmetic_key),
        )
        conn.commit()
        return True, f"Crafted {cosmetic_key} (-{cost} coins)."
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"craft_cosmetic error: {e}")
        return False, "Craft failed."
    finally:
        conn.close()


def purchase_casino_reward(player_name, reward_key):
    reward = CASINO_REWARD_SHOP.get(reward_key)
    if reward is None:
        return False, 'Unknown reward.'
    conn = create_connection()
    if conn is None:
        return False, 'No database connection.'
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False, 'Player not found.'
        _ensure_casino_stats_row(conn, player_id)
        cost = int(reward.get('cost', 0))
        chips = get_total_chips(conn, player_name)
        profile = get_casino_profile(player_name)
        required_rep = int(reward.get('required_reputation', 0) or 0)
        if chips < cost:
            return False, f'Need {cost} chips (have {chips}).'
        if int(profile.get('reputation', 0) or 0) < required_rep:
            return False, f'Need {required_rep} casino reputation for this reward.'

        cosmetic_key = str(reward.get('yield', reward_key))
        cursor = conn.cursor()
        cursor.execute(
            'SELECT quantity FROM player_cosmetics WHERE player_id = ? AND cosmetic_key = ?',
            (int(player_id), cosmetic_key),
        )
        row = cursor.fetchone()
        if row and int(row[0] or 0) > 0:
            return False, 'Reward already owned.'

        subtract_total_chips(conn, player_name, cost)
        cursor.execute(
            '''
            INSERT INTO player_cosmetics (player_id, cosmetic_key, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(player_id, cosmetic_key)
            DO UPDATE SET quantity = quantity + 1, updated_date = CURRENT_TIMESTAMP
            ''',
            (int(player_id), cosmetic_key),
        )
        cursor.execute(
            'UPDATE players SET casino_reputation = casino_reputation + ? WHERE player_id = ?',
            (max(1, cost // 35), int(player_id)),
        )
        conn.commit()
        return True, f"Purchased {reward.get('label', cosmetic_key)} for {cost} chips."
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"purchase_casino_reward error: {e}")
        return False, 'Prize counter purchase failed.'
    finally:
        conn.close()


def _medal_rank_value(medal):
    order = {'none': 0, 'bronze': 1, 'silver': 2, 'gold': 3}
    return order.get(str(medal or 'none').lower(), 0)


def get_training_trial_progress(player_name):
    conn = create_connection()
    if conn is None:
        return {}
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return {}
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT trial_key, best_medal, best_time, best_deaths, completion_count
            FROM player_training_trials
            WHERE player_id = ?
            ''',
            (int(player_id),),
        )
        rows = cursor.fetchall()
        out = {}
        for row in rows:
            out[str(row[0])] = {
                'best_medal': str(row[1] or 'none'),
                'best_time': float(row[2]) if row[2] is not None else None,
                'best_deaths': int(row[3]) if row[3] is not None else None,
                'completion_count': int(row[4] or 0),
            }
        return out
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_training_trial_progress error: {e}")
        return {}
    finally:
        conn.close()


def save_training_trial_result(player_name, trial_key, medal, completion_time, death_count):
    conn = create_connection()
    if conn is None:
        return {'ok': False, 'new_medal': False, 'new_best_time': False, 'best_medal': 'none', 'reward_coins': 0, 'reward_token': None}
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return {'ok': False, 'new_medal': False, 'new_best_time': False, 'best_medal': 'none', 'reward_coins': 0, 'reward_token': None}

        normalized = str(medal or 'none').lower()
        if normalized not in ('none', 'bronze', 'silver', 'gold'):
            normalized = 'none'

        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT best_medal, best_time, completion_count
            FROM player_training_trials
            WHERE player_id = ? AND trial_key = ?
            ''',
            (int(player_id), str(trial_key)),
        )
        row = cursor.fetchone()

        prev_medal = str((row[0] if row else 'none') or 'none')
        prev_time = float(row[1]) if row and row[1] is not None else None
        prev_count = int(row[2] or 0) if row else 0
        new_medal = _medal_rank_value(normalized) > _medal_rank_value(prev_medal)
        new_best_time = (prev_time is None or float(completion_time) < prev_time)
        stored_medal = normalized if new_medal else prev_medal
        stored_time = float(completion_time) if new_best_time else prev_time
        reward_coins = int(TRAINING_TRIAL_REWARD_MAP.get(normalized, 0)) if new_medal else 0
        reward_token = None

        cursor.execute(
            '''
            INSERT INTO player_training_trials (player_id, trial_key, best_medal, best_time, best_deaths, completion_count)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(player_id, trial_key)
            DO UPDATE SET best_medal = ?,
                          best_time = ?,
                          best_deaths = ?,
                          completion_count = ?,
                          updated_date = CURRENT_TIMESTAMP
            ''',
            (
                int(player_id),
                str(trial_key),
                stored_medal,
                stored_time,
                int(death_count),
                stored_medal,
                stored_time,
                int(death_count),
                prev_count + 1,
            ),
        )

        if reward_coins > 0:
            add_total_coins(conn, player_name, reward_coins)

        if new_medal and normalized in ('bronze', 'silver', 'gold'):
            reward_token = f"training_token_{str(trial_key)}_{normalized}"
            cursor.execute(
                '''
                INSERT INTO player_cosmetics (player_id, cosmetic_key, quantity)
                VALUES (?, ?, 1)
                ON CONFLICT(player_id, cosmetic_key)
                DO UPDATE SET quantity = quantity + 1, updated_date = CURRENT_TIMESTAMP
                ''',
                (int(player_id), reward_token),
            )

        conn.commit()
        return {
            'ok': True,
            'new_medal': bool(new_medal),
            'new_best_time': bool(new_best_time),
            'best_medal': stored_medal,
            'reward_coins': int(reward_coins),
            'reward_token': reward_token,
        }
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"save_training_trial_result error: {e}")
        return {'ok': False, 'new_medal': False, 'new_best_time': False, 'best_medal': 'none', 'reward_coins': 0, 'reward_token': None}
    finally:
        conn.close()


def _ensure_prestige_row(conn, player_id):
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT OR IGNORE INTO player_prestige (player_id, prestige_level, prestige_points)
        VALUES (?, 0, 0)
        ''',
        (int(player_id),),
    )


def get_prestige_profile(player_name):
    conn = create_connection()
    if conn is None:
        return {'prestige_level': 0, 'prestige_points': 0}
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return {'prestige_level': 0, 'prestige_points': 0}
        _ensure_prestige_row(conn, player_id)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT prestige_level, prestige_points FROM player_prestige WHERE player_id = ?',
            (int(player_id),),
        )
        row = cursor.fetchone()
        conn.commit()
        return {
            'prestige_level': int((row or [0, 0])[0] or 0),
            'prestige_points': int((row or [0, 0])[1] or 0),
        }
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_prestige_profile error: {e}")
        return {'prestige_level': 0, 'prestige_points': 0}
    finally:
        conn.close()


def add_prestige_points(player_name, points):
    conn = create_connection()
    if conn is None:
        return False
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        _ensure_prestige_row(conn, player_id)
        cursor = conn.cursor()
        cursor.execute(
            '''
            UPDATE player_prestige
            SET prestige_points = prestige_points + ?,
                updated_date = CURRENT_TIMESTAMP
            WHERE player_id = ?
            ''',
            (max(0, int(points)), int(player_id)),
        )
        conn.commit()
        return True
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"add_prestige_points error: {e}")
        return False
    finally:
        conn.close()


def attempt_prestige(player_name, required_points=1200):
    conn = create_connection()
    if conn is None:
        return False, "No database connection."
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False, "Player not found."
        _ensure_prestige_row(conn, player_id)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT prestige_level, prestige_points FROM player_prestige WHERE player_id = ?',
            (int(player_id),),
        )
        row = cursor.fetchone() or (0, 0)
        lvl = int(row[0] or 0)
        pts = int(row[1] or 0)
        if pts < int(required_points):
            return False, f"Need {required_points} prestige points (have {pts})."

        cursor.execute(
            '''
            UPDATE player_prestige
            SET prestige_level = prestige_level + 1,
                prestige_points = prestige_points - ?,
                updated_date = CURRENT_TIMESTAMP
            WHERE player_id = ?
            ''',
            (int(required_points), int(player_id)),
        )
        # Soft reset meta upgrades while preserving cosmetic account progression.
        cursor.execute(
            '''
            UPDATE player_meta_upgrades
            SET mobility_level = 0,
                survivability_level = 0,
                economy_level = 0,
                updated_date = CURRENT_TIMESTAMP
            WHERE player_id = ?
            ''',
            (int(player_id),),
        )
        conn.commit()
        return True, f"Prestige advanced to Lv {lvl + 1}."
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"attempt_prestige error: {e}")
        return False, "Prestige failed."
    finally:
        conn.close()


def save_daily_challenge_run(player_name, date_key, level_id, seed, challenge_code, score, completion_time, coins_collected=0):
    conn = create_connection()
    if conn is None:
        return False
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO daily_challenge_runs
            (date_key, level_id, seed, challenge_code, player_id, score, completion_time, coins_collected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                str(date_key),
                int(level_id),
                int(seed),
                str(challenge_code),
                int(player_id),
                int(score),
                float(completion_time),
                int(coins_collected),
            ),
        )
        conn.commit()
        return True
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"save_daily_challenge_run error: {e}")
        return False
    finally:
        conn.close()


def get_daily_challenge_top_scores(date_key, limit=10):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT p.player_name, MAX(d.score) AS best_score
            FROM daily_challenge_runs d
            JOIN players p ON p.player_id = d.player_id
            WHERE d.date_key = ?
            GROUP BY d.player_id
            ORDER BY best_score DESC
            LIMIT ?
            ''',
            (str(date_key), int(limit)),
        )
        return cursor.fetchall()
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_daily_challenge_top_scores error: {e}")
        return []
    finally:
        conn.close()


def get_daily_challenge_top_times(date_key, limit=10):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT p.player_name, MIN(d.completion_time) AS best_time
            FROM daily_challenge_runs d
            JOIN players p ON p.player_id = d.player_id
            WHERE d.date_key = ?
            GROUP BY d.player_id
            ORDER BY best_time ASC
            LIMIT ?
            ''',
            (str(date_key), int(limit)),
        )
        return cursor.fetchall()
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_daily_challenge_top_times error: {e}")
        return []
    finally:
        conn.close()


def _ensure_meta_upgrade_row(conn, player_id):
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT OR IGNORE INTO player_meta_upgrades (player_id, mobility_level, survivability_level, economy_level)
        VALUES (?, 0, 0, 0)
        ''',
        (int(player_id),),
    )


def get_meta_upgrades(player_name):
    conn = create_connection()
    if conn is None:
        return {'mobility': 0, 'survivability': 0, 'economy': 0}
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return {'mobility': 0, 'survivability': 0, 'economy': 0}
        _ensure_meta_upgrade_row(conn, player_id)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT mobility_level, survivability_level, economy_level FROM player_meta_upgrades WHERE player_id = ?',
            (int(player_id),),
        )
        row = cursor.fetchone()
        conn.commit()
        if not row:
            return {'mobility': 0, 'survivability': 0, 'economy': 0}
        return {
            'mobility': int(row[0] or 0),
            'survivability': int(row[1] or 0),
            'economy': int(row[2] or 0),
        }
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_meta_upgrades error: {e}")
        return {'mobility': 0, 'survivability': 0, 'economy': 0}
    finally:
        conn.close()


def purchase_meta_upgrade(player_name, stat_key):
    conn = create_connection()
    if conn is None:
        return False, "No database connection."
    stat_to_col = {
        'mobility': 'mobility_level',
        'survivability': 'survivability_level',
        'economy': 'economy_level',
    }
    if stat_key not in stat_to_col:
        return False, "Unknown upgrade type."
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False, "Player not found."

        _ensure_meta_upgrade_row(conn, player_id)
        col = stat_to_col[stat_key]
        cursor = conn.cursor()
        cursor.execute(f'SELECT {col} FROM player_meta_upgrades WHERE player_id = ?', (int(player_id),))
        row = cursor.fetchone()
        current_level = int(row[0] or 0) if row else 0
        if current_level >= 10:
            return False, f"{stat_key.title()} is already maxed."

        cost = 120 + current_level * 90
        total_coins = get_total_coins(conn, player_name)
        if total_coins < cost:
            return False, f"Need {cost} coins (have {total_coins})."

        subtract_total_coins(conn, player_name, cost)
        cursor.execute(
            f'''
            UPDATE player_meta_upgrades
            SET {col} = {col} + 1,
                updated_date = CURRENT_TIMESTAMP
            WHERE player_id = ?
            ''',
            (int(player_id),),
        )
        conn.commit()
        return True, f"{stat_key.title()} upgraded to Lv {current_level + 1} (-{cost} coins)."
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"purchase_meta_upgrade error: {e}")
        return False, "Upgrade failed."
    finally:
        conn.close()


def add_friend(conn, player_name, friend_name):
    try:
        if not friend_name or player_name == friend_name:
            return False
        player_id = add_player(conn, player_name)
        friend_id = add_player(conn, friend_name)
        if not player_id or not friend_id:
            return False
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO player_friends (player_id, friend_id) VALUES (?, ?)',
            (player_id, friend_id)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"add_friend error: {e}")
        return False


def remove_friend(conn, player_name, friend_name):
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        pr = cursor.fetchone()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (friend_name,))
        fr = cursor.fetchone()
        if not pr or not fr:
            return False
        cursor.execute('DELETE FROM player_friends WHERE player_id = ? AND friend_id = ?', (pr[0], fr[0]))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"remove_friend error: {e}")
        return False


def get_friends(player_name):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        if not row:
            return []
        pid = row[0]
        cursor.execute('''
            SELECT p.player_name
            FROM player_friends f
            JOIN players p ON p.player_id = f.friend_id
            WHERE f.player_id = ?
            ORDER BY p.player_name
        ''', (pid,))
        return [r[0] for r in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"get_friends error: {e}")
        return []
    finally:
        conn.close()


def set_profile_title(conn, player_name, title):
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET profile_title = ? WHERE player_id = ?', (title, player_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"set_profile_title error: {e}")
        return False


def set_profile_badge(conn, player_name, badge):
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET profile_badge = ? WHERE player_id = ?', (badge, player_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"set_profile_badge error: {e}")
        return False


def get_profile_card(player_name):
    conn = create_connection()
    if conn is None:
        return {}
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT player_id, profile_title, profile_badge, active_skin, coins_collected
            FROM players WHERE player_name = ?
        ''', (player_name,))
        row = cursor.fetchone()
        if not row:
            return {}
        player_id, title, badge, skin, coins = row

        cursor.execute('SELECT MAX(score) FROM scores WHERE player_id = ?', (player_id,))
        best_score = cursor.fetchone()[0] or 0
        cursor.execute('SELECT MIN(completion_time) FROM times WHERE player_id = ?', (player_id,))
        best_time = cursor.fetchone()[0]

        return {
            'player_name': player_name,
            'title': title or 'Rookie Explorer',
            'badge': badge or 'none',
            'skin': skin or 'default',
            'coins': coins or 0,
            'best_score': best_score,
            'best_time': best_time,
        }
    except sqlite3.Error as e:
        print(f"get_profile_card error: {e}")
        return {}
    finally:
        conn.close()


def log_analytics_event(player_name, event_type, level_id=None, x=None, y=None, meta=None):
    conn = create_connection()
    if conn is None:
        return False
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO analytics_events (player_id, level_id, event_type, x, y, meta)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (player_id, level_id, event_type, x, y, meta))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"log_analytics_event error: {e}")
        return False
    finally:
        conn.close()


def get_analytics_heatmap(player_name, level_id, event_type='death', limit=20):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        if not row:
            return []
        pid = row[0]
        cursor.execute('''
            SELECT x, y, COUNT(*) as c
            FROM analytics_events
            WHERE player_id = ? AND level_id = ? AND event_type = ?
            GROUP BY x, y
            ORDER BY c DESC
            LIMIT ?
        ''', (pid, level_id, event_type, limit))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"get_analytics_heatmap error: {e}")
        return []
    finally:
        conn.close()


def get_player_performance_summary(player_name, sample_limit=20):
    conn = create_connection()
    if conn is None:
        return {
            'runs_sampled': 0,
            'avg_frame_ms': None,
            'p95_frame_ms': None,
            'avg_fps': None,
            'avg_mem_mb': None,
            'peak_mem_mb': None,
            'perf_spikes': 0,
        }
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        if not row:
            return {
                'runs_sampled': 0,
                'avg_frame_ms': None,
                'p95_frame_ms': None,
                'avg_fps': None,
                'avg_mem_mb': None,
                'peak_mem_mb': None,
                'perf_spikes': 0,
            }
        player_id = int(row[0])
        lim = max(1, int(sample_limit))

        cursor.execute(
            '''
            SELECT COUNT(*), AVG(x), AVG(y)
            FROM (
                SELECT x, y
                FROM analytics_events
                WHERE player_id = ? AND event_type = 'perf_summary'
                ORDER BY event_id DESC
                LIMIT ?
            )
            ''',
            (player_id, lim),
        )
        stats_row = cursor.fetchone() or (0, None, None)
        runs_sampled = int(stats_row[0] or 0)
        avg_frame_ms = None if stats_row[1] is None else (float(stats_row[1]) / 100.0)
        p95_frame_ms = None if stats_row[2] is None else (float(stats_row[2]) / 100.0)

        cursor.execute(
            '''
            SELECT meta
            FROM analytics_events
            WHERE player_id = ? AND event_type = 'perf_summary'
            ORDER BY event_id DESC
            LIMIT ?
            ''',
            (player_id, lim),
        )
        avg_fps_samples = []
        avg_mem_samples = []
        peak_mem_samples = []
        for (meta_raw,) in cursor.fetchall():
            try:
                payload = json.loads(meta_raw) if meta_raw else {}
            except Exception:
                payload = {}
            if isinstance(payload, dict):
                if payload.get('fps_avg') is not None:
                    avg_fps_samples.append(float(payload.get('fps_avg')))
                if payload.get('mem_current_mb') is not None:
                    avg_mem_samples.append(float(payload.get('mem_current_mb')))
                if payload.get('mem_peak_mb') is not None:
                    peak_mem_samples.append(float(payload.get('mem_peak_mb')))

        cursor.execute(
            '''
            SELECT COUNT(*)
            FROM analytics_events
            WHERE player_id = ? AND event_type = 'perf_spike'
            ''',
            (player_id,),
        )
        perf_spikes = int((cursor.fetchone() or [0])[0] or 0)

        return {
            'runs_sampled': runs_sampled,
            'avg_frame_ms': avg_frame_ms,
            'p95_frame_ms': p95_frame_ms,
            'avg_fps': (sum(avg_fps_samples) / len(avg_fps_samples)) if avg_fps_samples else None,
            'avg_mem_mb': (sum(avg_mem_samples) / len(avg_mem_samples)) if avg_mem_samples else None,
            'peak_mem_mb': max(peak_mem_samples) if peak_mem_samples else None,
            'perf_spikes': perf_spikes,
        }
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"get_player_performance_summary error: {e}")
        return {
            'runs_sampled': 0,
            'avg_frame_ms': None,
            'p95_frame_ms': None,
            'avg_fps': None,
            'avg_mem_mb': None,
            'peak_mem_mb': None,
            'perf_spikes': 0,
        }
    finally:
        conn.close()


def get_player_stats(player_name):
    conn = create_connection()
    if conn is None:
        return {}
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        if not row:
            return {}
        player_id = row[0]

        cursor.execute('SELECT COUNT(*), MAX(score), AVG(score) FROM scores WHERE player_id = ?', (player_id,))
        score_stats = cursor.fetchone()

        cursor.execute('SELECT COUNT(*), MIN(completion_time), AVG(completion_time) FROM times WHERE player_id = ?', (player_id,))
        time_stats = cursor.fetchone()

        return {
            'total_scores': score_stats[0],
            'highest_score': score_stats[1],
            'average_score': score_stats[2],
            'total_times': time_stats[0],
            'fastest_time': time_stats[1],
            'average_time': time_stats[2]
        }
    except sqlite3.Error as e:
        print(f"get_player_stats error: {e}")
        return {}
    finally:
        conn.close()

def unlock_level(conn, player_name, level_id):
    """Mark a level as completed/unlocked for a player"""
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        # Use INSERT OR IGNORE to handle duplicates (player already completed level)
        cursor.execute('''
            INSERT OR IGNORE INTO player_levels (player_id, level_id, completed, completion_date)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
        ''', (player_id, level_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"unlock_level error: {e}")
        return False


def get_unlocked_levels(player_name):
    """Return list of level IDs that player has completed"""
    conn = create_connection()
    if conn is None:
        return [1, 14]  # Default: tutorial + first optional unlocked
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        if not row:
            return [1, 14]  # New player: tutorial + first optional unlocked
        player_id = row[0]
        
        cursor.execute('SELECT level_id FROM player_levels WHERE player_id = ? AND completed = 1 ORDER BY level_id', (player_id,))
        rows = cursor.fetchall()
        unlocked = [row[0] for row in rows]
        
        # Always include baseline levels
        if not unlocked:
            return [1, 14]
        if 1 not in unlocked:
            unlocked.append(1)
        if 14 not in unlocked:
            unlocked.append(14)
        unlocked.sort()
        return unlocked
    except sqlite3.Error as e:
        print(f"get_unlocked_levels error: {e}")
        return [1, 14]
    finally:
        conn.close()


def is_level_locked(player_name, level_id):
    """Check if a level is locked for a player"""
    if level_id == 14:
        return False
    unlocked = get_unlocked_levels(player_name)
    return level_id not in unlocked


def is_hard_mode_unlocked(player_name):
    """Check if hard mode is unlocked (normal boss complete)"""
    unlocked = get_unlocked_levels(player_name)
    return 12 in unlocked or 7 in unlocked


def is_hard_mode_enabled(player_name):
    """Check if hard mode is currently enabled in settings"""
    conn = create_connection()
    if conn is None:
        return False
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute('SELECT hard_mode_enabled FROM players WHERE player_id = ?', (player_id,))
        row = cursor.fetchone()
        result = row[0] if row and row[0] else False
        conn.close()
        return result
    except sqlite3.Error as e:
        print(f"is_hard_mode_enabled error: {e}")
        conn.close()
        return False


def set_hard_mode(conn, player_name, enabled):
    """Enable or disable hard mode for a player"""
    try:
        player_id = add_player(conn, player_name)
        if not player_id:
            return False
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET hard_mode_enabled = ? WHERE player_id = ?', 
                       (1 if enabled else 0, player_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"set_hard_mode error: {e}")
        return False


def _hash_password(password, salt_hex=None):
    if salt_hex is None:
        salt_hex = binascii.hexlify(os.urandom(16)).decode("ascii")
    salt = binascii.unhexlify(salt_hex.encode("ascii"))
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return binascii.hexlify(digest).decode("ascii"), salt_hex


def player_exists(conn, player_name):
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM players WHERE player_name = ?', (player_name,))
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        print(f"player_exists error: {e}")
        return False


def validate_password_strength(password):
    if password is None:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not any(ch.islower() for ch in password):
        return False, "Password needs a lowercase letter."
    if not any(ch.isupper() for ch in password):
        return False, "Password needs an uppercase letter."
    if not any(ch.isdigit() for ch in password):
        return False, "Password needs a number."
    if not any((not ch.isalnum()) for ch in password):
        return False, "Password needs a symbol."
    return True, ""


def register_player(conn, player_name, password):
    try:
        clean_name = (player_name or "").strip()
        if not clean_name or not password:
            return False, "Name and password are required."
        if len(clean_name) > 20:
            return False, "Name must be 20 characters or fewer."
        ok_strength, strength_msg = validate_password_strength(password)
        if not ok_strength:
            return False, strength_msg
        if player_exists(conn, clean_name):
            return False, "That name is already taken."

        password_hash, salt_hex = _hash_password(password)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO players (player_name, password_hash, password_salt) VALUES (?, ?, ?)',
            (clean_name, password_hash, salt_hex)
        )
        player_id = cursor.lastrowid
        cursor.execute(
            '''
            INSERT OR IGNORE INTO player_levels (player_id, level_id, completed)
            VALUES (?, 1, 1)
            ''',
            (player_id,)
        )
        cursor.execute(
            '''
            INSERT OR IGNORE INTO player_levels (player_id, level_id, completed)
            VALUES (?, 14, 1)
            ''',
            (player_id,)
        )
        conn.commit()
        return True, clean_name
    except sqlite3.Error as e:
        print(f"register_player error: {e}")
        return False, "Could not register right now."


def authenticate_player(conn, player_name, password):
    try:
        clean_name = (player_name or "").strip()
        if not clean_name or not password:
            return False, "Name and password are required."

        cursor = conn.cursor()
        cursor.execute(
            'SELECT player_id, password_hash, password_salt FROM players WHERE player_name = ?',
            (clean_name,)
        )
        row = cursor.fetchone()
        if not row:
            return False, "Account not found."

        player_id, stored_hash, stored_salt = row

        # Backward-compatible path: existing accounts without a password can claim one once.
        if not stored_hash or not stored_salt:
            new_hash, new_salt = _hash_password(password)
            cursor.execute(
                'UPDATE players SET password_hash = ?, password_salt = ? WHERE player_id = ?',
                (new_hash, new_salt, player_id)
            )
            conn.commit()
            return True, clean_name

        candidate_hash, _ = _hash_password(password, stored_salt)
        if hmac.compare_digest(candidate_hash, stored_hash):
            return True, clean_name
        return False, "Incorrect password."
    except sqlite3.Error as e:
        print(f"authenticate_player error: {e}")
        return False, "Could not log in right now."


def add_player(conn, player_name):
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO players (player_name) VALUES (?)', (player_name,))
        player_id = cursor.lastrowid
        # Unlock tutorial (level 1) for new player
        cursor.execute('''
            INSERT OR IGNORE INTO player_levels (player_id, level_id, completed)
            VALUES (?, 1, 1)
        ''', (player_id,))
        cursor.execute('''
            INSERT OR IGNORE INTO player_levels (player_id, level_id, completed)
            VALUES (?, 14, 1)
        ''', (player_id,))
        conn.commit()
        return player_id
    except sqlite3.IntegrityError:
        # existing player - just return their ID
        cursor = conn.cursor()
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        row = cursor.fetchone()
        return row[0] if row else None

def view():
    conn = create_connection()
    if conn is None:
        print("Failed to open database.")
        return
    try:
        print("Database contents:")
        print(" Player_ID | Player_Name | Created_Date | Coins_Collected | Lives | Float power | Invincibility power | Fire power")
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM players')
        players = cursor.fetchall()
        print("Players:")
        for player in players:
            print(player)
    except sqlite3.Error as e:
        print(f"view error: {e}")
    finally:
        conn.close()

def clear_database():
    conn = create_connection()
    if conn is None:
        print("Failed to open database.")
        return
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM players')
        cursor.execute('DELETE FROM scores')
        cursor.execute('DELETE FROM times')
        cursor.execute('DELETE FROM player_levels')
        cursor.execute('DELETE FROM survival_scores')
        cursor.execute('DELETE FROM player_friends')
        cursor.execute('DELETE FROM analytics_events')
        conn.commit()
        print("Database cleared.")
    except sqlite3.Error as e:
        print(f"clear_database error: {e}")
    finally:
        conn.close()

# For testing purposes
#view()

if __name__ == "__main__":
    initialize_database()
