# Master Game Improvements Roadmap

Status key:
- DONE: fully implemented
- IN-PROGRESS: actively implemented and partially complete
- NEXT: highest-priority queued task
- PLANNED: scoped but not started

## Milestone 1 - Style + Feedback (DONE)
- DONE: Movement actions (air dash, slide, slide jump, wall jump) contribute to style points.
- DONE: Live in-level style meter with rank/next-target guidance.
- DONE: Win screen style breakdown panel (kills, movement, finishers, penalties).
- DONE: Add variation bonuses and repeated-action diminishing returns.
- DONE: Add style decay over time outside active combat.

## Milestone 2 - Training Trials (IN-PROGRESS)
- DONE: Convert training playground into selectable medal-based trials.
- DONE: Add per-trial ghost target timing and in-level delta HUD feedback.
- DONE: Persist trial best medal/time and clear counts per player.
- DONE: Reward medal tier upgrades with coin payouts.
- DONE: Add trial-specific cosmetic token rewards on medal tier upgrades.
- DONE: Surface earned training tokens in profile card UI.

## Milestone 3 - World Identity (DONE)
- DONE: Add signature World 3 siege-strike mechanic with dedicated hazards/enemy interactions.
- DONE: Add world-specific tutorials and challenge variants.

## Milestone 4 - Boss Replayability (DONE)
- DONE: Add rotating weekly boss modifiers.
- DONE: Keep one stable core pattern + one rotating pattern for readability.

## Milestone 5 - Economy + Shop Expansion (DONE)
- DONE: Separate Casino District with chips economy.
- DONE: Daily casino bonus, buy-ins, rotating prize counter baseline.
- DONE: Remove remaining economy coupling points and tune payouts.
- DONE: Expand main shop into clearer merchant categories.
- DONE: Add clearer distinctions between consumables, cosmetics, and premium vendors.

## Milestone 6 - Casino Depth (DONE)
- DONE: Dedicated casino hub with blackjack, roulette, and slots using chips.
- DONE: Casino stats ledger and reputation tracking.
- DONE: Add casino quests (daily/weekly).
- DONE: Add VIP unlock track tied to reputation.
- DONE: Add one skill-based casino minigame.
- DONE: Add table-specific dealers, dialogue, and stronger theming.

## Milestone 7 - Hub + Social (DONE)
- DONE: Add NPCs with unlock-reactive dialogue/events.
- DONE: Add weekly featured custom-level playlist and social challenge hooks.

## Milestone 8 - Performance + Accessibility (DONE)
- DONE: Frame-time and memory metrics in debug overlay.
- DONE: HUD simplification mode and colorblind-safe cue palette.
- DONE: Telemetry polish with frame-spike event logging and hub performance summary.

## Suggested Delivery Order
1. Milestone 2
2. Milestone 6 depth pass
3. Milestone 5 shop expansion
4. Milestone 3
5. Milestone 4
6. Milestone 7
7. Milestone 8

## Notes
- This roadmap is intentionally staged to avoid destabilizing core gameplay while broad systems are being added.
- Large milestones should be shipped in slices with playtest checkpoints after each slice.