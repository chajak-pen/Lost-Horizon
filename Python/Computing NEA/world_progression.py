WORLD_DEFS = {
    1: {
        "name": "World 1",
        "normal_levels": [2, 3, 4, 5, 6],
        "normal_boss": 12,
        "hard_levels": [7, 8, 9, 10, 11],
        "hard_boss": 13,
        "optional_levels": [14, 15, 16],
    },
    2: {
        "name": "World 2",
        "normal_levels": [17, 18, 19, 20, 21],
        "normal_boss": 22,
        "hard_levels": [23, 24, 25, 26, 27],
        "hard_boss": 28,
        "optional_levels": [],
    },
    3: {
        "name": "World 3",
        "normal_levels": [29, 30, 31, 32, 33],
        "normal_boss": 34,
        "hard_levels": [35, 36, 37, 38, 39],
        "hard_boss": 40,
        "optional_levels": [],
    },
}

WORLD_ORDER = sorted(WORLD_DEFS.keys())
TUTORIAL_LEVEL = 1

# Challenge clears can open branch routes early.
CHALLENGE_BRANCH_UNLOCKS = {
    2: [7],
    3: [14],
    4: [15],
    5: [16],
    17: [23],
    18: [24],
    29: [35],
    30: [36],
}


def world_name(world_id):
    return WORLD_DEFS.get(world_id, {}).get("name", f"World {world_id}")


def is_world_unlocked(unlocked_levels, world_id):
    if world_id == 1:
        return True
    prev_world = world_id - 1
    prev_boss = WORLD_DEFS.get(prev_world, {}).get("normal_boss")
    return prev_boss in unlocked_levels


def _is_world_hard_unlocked_with_set(unlocked_set, world_id):
    world = WORLD_DEFS.get(world_id)
    if not world:
        return False

    # Current world normal progression must be complete.
    required_current = set(world["normal_levels"] + [world["normal_boss"]])
    if not required_current.issubset(unlocked_set):
        return False

    # World 1 hard unlocks from its own normal completion.
    if world_id == 1:
        return True

    # Later worlds require previous world's hard boss completion too.
    prev_world = WORLD_DEFS.get(world_id - 1)
    if not prev_world:
        return False
    return prev_world["hard_boss"] in unlocked_set


def is_world_hard_unlocked(unlocked_levels, world_id):
    return _is_world_hard_unlocked_with_set(set(unlocked_levels), world_id)


def highest_unlocked_normal_in_world(unlocked_levels, world_id):
    world = WORLD_DEFS.get(world_id)
    if not world:
        return None
    sequence = world["normal_levels"] + [world["normal_boss"]]
    highest = None
    for lvl in sequence:
        if lvl in unlocked_levels:
            highest = lvl
    return highest if highest is not None else sequence[0]


def compute_unlocks_after_completion(completed_level, unlocked_levels, challenge_completed=False):
    unlocked_set = set(unlocked_levels)
    unlocked_set.add(completed_level)
    to_unlock = set()

    # Always make sure tutorial completion opens the first world level.
    if completed_level == TUTORIAL_LEVEL:
        to_unlock.add(WORLD_DEFS[1]["normal_levels"][0])

    for world_id in WORLD_ORDER:
        world = WORLD_DEFS[world_id]

        normal_seq = world["normal_levels"] + [world["normal_boss"]]
        hard_seq = world["hard_levels"] + [world["hard_boss"]]
        optional_seq = world.get("optional_levels", [])

        # Sequential normal unlocks.
        for i, lvl in enumerate(normal_seq[:-1]):
            if completed_level == lvl:
                to_unlock.add(normal_seq[i + 1])

        # Sequential hard unlocks.
        for i, lvl in enumerate(hard_seq[:-1]):
            if completed_level == lvl:
                to_unlock.add(hard_seq[i + 1])

        # Sequential optional unlocks (world 1 only currently).
        for i, lvl in enumerate(optional_seq[:-1]):
            if completed_level == lvl:
                to_unlock.add(optional_seq[i + 1])

    # World access unlocks by normal boss completion of previous world.
    for world_id in WORLD_ORDER:
        if world_id == 1:
            continue
        if is_world_unlocked(unlocked_set, world_id):
            to_unlock.add(WORLD_DEFS[world_id]["normal_levels"][0])

    # Hard access unlocks by world rule.
    for world_id in WORLD_ORDER:
        if _is_world_hard_unlocked_with_set(unlocked_set, world_id):
            to_unlock.add(WORLD_DEFS[world_id]["hard_levels"][0])

    # Branch unlocks: optional or hard routes unlocked by challenge completion.
    if challenge_completed:
        for lvl in CHALLENGE_BRANCH_UNLOCKS.get(completed_level, []):
            to_unlock.add(lvl)

    return sorted(l for l in to_unlock if l not in unlocked_set)
