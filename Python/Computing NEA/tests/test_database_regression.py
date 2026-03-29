import os
import tempfile
import unittest

from database import (
    create_connection,
    initialize_database,
    save_score,
    save_time,
    save_level_medal,
    get_player_level_medal,
    get_high_scores,
    get_fastest_times,
    unlock_level,
    get_unlocked_levels,
)


class DatabaseRegressionTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self.conn = create_connection(self.db_path)
        initialize_database(self.conn)

    def tearDown(self):
        if self.conn:
            self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_save_and_load_score_and_time(self):
        ok_s = save_score(self.conn, 'tester', 1234, 20, 2)
        ok_t = save_time(self.conn, 'tester', 42.5, 20, 2)
        self.assertTrue(ok_s)
        self.assertTrue(ok_t)

        # Global accessors use default DB file; verify persistence by querying direct table instead.
        cur = self.conn.cursor()
        cur.execute('SELECT COUNT(*) FROM scores')
        self.assertGreaterEqual(cur.fetchone()[0], 1)
        cur.execute('SELECT COUNT(*) FROM times')
        self.assertGreaterEqual(cur.fetchone()[0], 1)

    def test_unlock_persistence(self):
        ok = unlock_level(self.conn, 'tester2', 5)
        self.assertTrue(ok)
        # unlock query uses default DB file in current implementation; verify direct row presence.
        cur = self.conn.cursor()
        cur.execute('''
            SELECT COUNT(*)
            FROM player_levels pl
            JOIN players p ON p.player_id = pl.player_id
            WHERE p.player_name = ? AND pl.level_id = ?
        ''', ('tester2', 5))
        self.assertEqual(cur.fetchone()[0], 1)

    def test_level_medal_persistence(self):
        ok = save_level_medal(self.conn, 'tester3', 2, 'bronze', 60.0, 4, 5, 10)
        self.assertTrue(ok)

        # Better medal should replace older one.
        ok_upgrade = save_level_medal(self.conn, 'tester3', 2, 'silver', 52.0, 2, 7, 10)
        self.assertTrue(ok_upgrade)

        # Worse medal should not downgrade best medal.
        ok_no_downgrade = save_level_medal(self.conn, 'tester3', 2, 'bronze', 45.0, 1, 9, 10)
        self.assertTrue(ok_no_downgrade)

        cur = self.conn.cursor()
        cur.execute('''
            SELECT plm.medal
            FROM player_level_medals plm
            JOIN players p ON p.player_id = plm.player_id
            WHERE p.player_name = ? AND plm.level_id = ?
        ''', ('tester3', 2))
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'silver')


if __name__ == '__main__':
    unittest.main()
