import unittest

from world_progression import compute_unlocks_after_completion, WORLD_DEFS


class ProgressionTests(unittest.TestCase):
    def test_tutorial_unlocks_world1_level1(self):
        unlocks = compute_unlocks_after_completion(1, [1, 14])
        self.assertIn(WORLD_DEFS[1]['normal_levels'][0], unlocks)

    def test_world1_normal_chain_unlock(self):
        l1 = WORLD_DEFS[1]['normal_levels'][0]
        l2 = WORLD_DEFS[1]['normal_levels'][1]
        unlocks = compute_unlocks_after_completion(l1, [1, 14, l1])
        self.assertIn(l2, unlocks)

    def test_world2_entry_unlocks_after_world1_boss(self):
        boss1 = WORLD_DEFS[1]['normal_boss']
        w2_first = WORLD_DEFS[2]['normal_levels'][0]
        unlocks = compute_unlocks_after_completion(boss1, [1, 14, boss1])
        self.assertIn(w2_first, unlocks)

    def test_challenge_completion_unlocks_branch(self):
        unlocks = compute_unlocks_after_completion(2, [1, 2, 14], challenge_completed=True)
        self.assertIn(WORLD_DEFS[1]['hard_levels'][0], unlocks)


if __name__ == '__main__':
    unittest.main()
