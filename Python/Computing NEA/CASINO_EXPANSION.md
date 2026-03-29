# Casino District Expansion

## Goal
- Add a separate casino area that complements the main platforming loop instead of replacing it.
- Keep level progression currency and casino gambling currency separate.
- Use the casino as a side hub for table games, rotating rewards, repeat visits, and cosmetic progression.

## Implemented First Slice
- New Casino District hub screen reachable from the start menu.
- Separate chips economy backed by `players.casino_chips`.
- Casino reputation backed by `players.casino_reputation`.
- Persistent casino stats table tracking wagered chips, payouts, and per-game counts.
- Daily cashier bonus for repeat visits.
- One-way buy-in exchange from coins to chips.
- Reused table games running on chips instead of coins: blackjack, roulette, slot machine.
- Rotating prize counter inventory that sells casino-themed cosmetic collectibles.

## Design Rules
- Coins remain the main progression currency for core gameplay and the main shop.
- Chips are the casino-only currency used for table play and prize counter purchases.
- Casino losses should never directly delete powerups, medals, or completed level progress.
- Buy-ins are one-way to prevent using the casino as a risk-free coin printer.
- Rewards from the casino should focus on cosmetics, collectibles, profile flair, and prestige-side progression.

## NPC / Area Structure
- Cashier: daily bonus, buy-ins, later cashout rules or VIP entry.
- Table Floor: blackjack, roulette, slots, later high-low and skill-based machines.
- Prize Counter: rotating weekly stock of chip-only rewards.
- VIP Lounge: future unlock for high reputation players.

## Next Implementation Steps
1. DONE: Move the remaining casino-related navigation out of the main shop so the separation is cleaner.
2. DONE: Add a skill-based Safecracker table so the district is not purely RNG-driven.
3. DONE: Add casino quests such as `play 3 casino rounds` and `wager 360 chips this week`.
4. DONE: Surface casino quest progress and reward locks in progression/casino screens.
5. DONE: Add VIP unlocks tied to casino reputation thresholds.
6. DONE: Add table-specific dealers, dialogue, and stronger theming so the area feels like a location rather than a menu.
7. NEXT: Add a dedicated VIP lounge room or event layer for high-reputation players.

## Shop Direction
- Keep the main shop focused on combat utility, lives, powerups, and skins.
- Keep the casino focused on chip spending, minigames, and side rewards.
- If the shop is expanded later, split it into clearer vendors: survival supplies, power vendor, skins, and prestige items.

## Risks To Watch
- Buy-in values can distort the economy if chips become too easy to earn.
- Casino rewards become pointless if they are not surfaced outside the casino hub.
- Table payout loops can undermine progression if they are balanced around coins instead of chips.
- If the prize counter stock is too static, the district will lose repeat-value quickly.