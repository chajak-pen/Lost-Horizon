-- Create the database for Lost Horizon game
CREATE TABLE IF NOT EXISTS players (
    player_id INTEGER PRIMARY KEY AUTOINCREMENT, '''#unique player identifier'''
    player_name TEXT NOT NULL UNIQUE, '''player name must be unique'''
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP '''date the player was created'''
);

-- Create a table for game scores (high scores)
CREATE TABLE IF NOT EXISTS scores (
    score_id INTEGER PRIMARY KEY AUTOINCREMENT, '''unique score identifier'''
    player_id INTEGER NOT NULL, '''references the player who achieved the score'''
    score INTEGER NOT NULL, '''the score achieved'''
    coins_collected INTEGER DEFAULT 0,  '''number of coins collected in the game'''
    difficulty TEXT DEFAULT 'normal', '''difficulty level of the game'''
    game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, '''date the game was played'''
    FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE  
     '''ensures referential integrity'''   
);

-- Create a table for fastest times
CREATE TABLE IF NOT EXISTS times (
    time_id INTEGER PRIMARY KEY AUTOINCREMENT, '''unique time identifier'''
    player_id INTEGER NOT NULL,     '''references the player who achieved the time'''
    completion_time REAL NOT NULL,  -- time in seconds '''time taken to complete the game'''
    coins_collected INTEGER DEFAULT 0, '''number of coins collected in the game'''
    difficulty TEXT DEFAULT 'normal', '''difficulty level of the game'''
    game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, '''date the game was played'''
    FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
        '''ensures referential integrity''' 
);

CREATE TABLE IF NOT EXISTS player_levels (
    player_id INTEGER NOT NULL,
    level_id INTEGER NOT NULL,
    PRIMARY KEY (player_id, level_id),
    FOREIGN KEY(player_id) REFERENCES players(player_id) ON DELETE CASCADE
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_scores_player ON scores(player_id); '''index on player_id for quick lookups'''
CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score DESC); '''index on score for retrieving high scores'''
CREATE INDEX IF NOT EXISTS idx_times_player ON times(player_id); '''index on player_id for quick lookups'''
CREATE INDEX IF NOT EXISTS idx_times_completion ON times(completion_time ASC); '''index on completion_time for retrieving fastest times'''
