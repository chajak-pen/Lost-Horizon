# Lost Horizon Feature Roadmap

Status key:
- DONE: implemented
- NEXT: queued next implementation target
- PLANNED: scoped and pending implementation

## Phase 0 - Foundation
- DONE: Sandbox Mode base flow (create/edit/save/play, world themes, public/private levels)
- DONE: Sandbox custom level persistence and leaderboards
- DONE: Player animation stabilization pass

## Phase 1 - Daily Challenge Run
- DONE: Deterministic daily challenge generation
- DONE: Daily challenge direct launch from play hub
- DONE: Daily challenge run persistence
- DONE: Daily challenge leaderboard viewer (score + time)

## Phase 2 - Rogue-lite Meta Upgrades
- DONE: Add upgrade tree schema (mobility, survivability, economy)
- DONE: Add quick upgrade purchase flow in hub (key U)
- DONE: Apply upgrade effects inside runtime (speed, HP, coin gain)

## Phase 3 - Boss Phases and Patterns
- DONE: Multi-phase thresholds and behavior table
- DONE: Distinct telegraph attacks per phase
- DONE: Difficulty scaling and readability polish

## Phase 4 - Replay Viewer
- DONE: Save complete replay timeline for best runs
- DONE: Add replay browser UI
- DONE: Playback controls (pause, scrub, speed)

## Phase 5 - Sandbox Expansion
- DONE: Prefab library
- DONE: Publish validation checks (start/finish/pathability)
- DONE: Creator profile metrics (plays, clears, likes)

## Phase 6 - Gameplay Depth
- DONE: New enemy archetypes (healer/summoner/teleport)
- DONE: Advanced hazards and biome-specific mechanics
- DONE: Expanded combo/style scoring rules

## Phase 7 - Progression and Economy
- DONE: Daily/weekly quests
- DONE: Cosmetic crafting economy
- DONE: Prestige loop with cosmetic progression

## Phase 8 - Quality and Accessibility
- DONE: Remappable controls and accessibility options
- DONE: Training playground for movement tech
- DONE: Analytics-guided onboarding improvements

## Phase 9 - Casino District
- DONE: Separate casino hub with chips economy and persistent stats
- DONE: Table games routed through casino-only chips instead of main progression coins
- DONE: Casino quests and VIP progression tied to reputation thresholds
- DONE: Add a skill-based casino minigame alongside the existing table games
- DONE: Deeper casino theming, dealers, and dialogue

## Phase 10 - Master Improvements Track
- DONE: Add live style meter and movement-tech style scoring support
- DONE: Add win screen style-rank breakdown by source category
- DONE: Training trials with medals, ghost targets, persistent best records, and cosmetic reward tokens
- DONE: World 3 signature mechanic pass with siege-strike hazards
- DONE: Weekly boss modifiers and rotating pattern layer
- DONE: Expanded shop vendor model
- DONE: Hub NPC progression events and social playlists
- DONE: Accessibility/performance instrumentation pass
- DONE: HUD simplification mode and colorblind-safe cue palette
- DONE: Accessibility/performance tuning and telemetry polish
- DONE: Style variation bonuses and repeated-action diminishing returns
- DONE: Style decay over time outside active combat
- DONE: World-specific tutorials and challenge variants
- NEXT: Master roadmap refresh and polish pass

## Delivery order
1. Phase 2
2. Phase 3
3. Phase 4
4. Phase 5
5. Phase 6
6. Phase 7
7. Phase 8
8. Phase 9
9. Phase 10

## Phase 11 - Version Next (Planned)

### 20 Improvement Backlog
1. Add selected power slot HUD indicator (1/2/3 + readiness).
2. Add keybind conflict warnings in controls settings and better way of changing keybinds(like common games such as fortnite where you have a menu to change each individual item instead of flicking through)
3. Add quick restart flow after death with brief safety delay.
4. Add checkpoint preview markers on level progress HUD.
5. Add optional projectile aim-assist slider under accessibility.
6. Add post-run mistake summary (deaths, stalls, major time loss).
7. Add relic system with three equip slots and tradeoff effects.
8. Add relic crafting with coins and rare fragments.
9. Add daily contracts with varied objective templates.
10. Add daily contract streak rewards and streak-safe persistence.
11. Add mastery tracks (movement, combat, speedrun).
12. Add prestige reset loop with account-wide perks.
13. Add rotating weekly world mutators.
14. Add boss phase variants per run seed.
15. Add elite enemy affixes with bonus rewards.
16. Add optional risk rooms with high-risk/high-reward choices.
17. Add challenge seed sharing for player-made challenge runs.
18. Add mini gauntlet mode (multi-level carryover run).
19. Add ghost rival challenges with asynchronous goals.
20. Add seasonal event pass with limited-time milestones.

### 4-Week Delivery Plan

#### Week 1 - Controls, HUD, and QoL
- Ship selected power slot HUD indicator.
- Ship keybind conflict detection/warnings.
- Ship quick restart flow after death.
- Ship post-run summary v1.

#### Week 2 - Replayability Layer
- Ship weekly world mutators.
- Ship boss phase variants.
- Add baseline telemetry for mutator usage and boss outcomes.

#### Week 3 - Progression Depth
- Ship relic loadout (3 slots).
- Ship relic crafting.
- Ship daily contracts + streak rewards.

#### Week 4 - Social Loop and Stabilization
- Ship ghost rival challenges.
- Run balance pass (economy, mutators, bosses).
- Complete regression testing and release notes.

### Priority
- Must: 1, 2, 7, 9, 13, 14.
- Should: 3, 6, 8, 10, 19.
- Could: 4, 5, 11, 12, 15, 16, 17, 18, 20.

### Dependencies
- Weekly mutators before final boss balance tuning.
- Relic data model before contract reward balancing.
- Save-schema migration before Week 4 QA freeze.

### Success Metrics
- Session length.
- Repeat runs per player.
- Daily return rate.
- Contract completion rate.
- Boss clear rate by variant.
- Keybind conflict incidence.
