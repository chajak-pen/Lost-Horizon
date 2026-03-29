import json
from pathlib import Path

from level_data import LEVELS


def summarize_level(level_id, cfg):
    enemies = len(cfg.get('melee_enemies', [])) + len(cfg.get('ranged_enemies', []))
    coins = len(cfg.get('coins', []))
    platforms = len(cfg.get('platforms', []))
    powerups = len(cfg.get('power_ups', []))
    hazards = len(cfg.get('rotating_firewalls', [])) + len(cfg.get('walls', []))
    density = round(enemies / max(1, platforms), 3)
    return {
        'level_id': level_id,
        'name': cfg.get('name', f'Level {level_id}'),
        'platforms': platforms,
        'enemies': enemies,
        'coins': coins,
        'powerups': powerups,
        'hazards': hazards,
        'enemy_platform_density': density,
        'suggestion': (
            'Increase coins' if coins < max(3, enemies) else
            'Add combat challenge' if enemies < max(2, platforms // 6) else
            'Balanced'
        )
    }


def build_report():
    rows = [summarize_level(lid, cfg) for lid, cfg in sorted(LEVELS.items())]
    out = {
        'level_count': len(rows),
        'levels': rows,
        'totals': {
            'platforms': sum(r['platforms'] for r in rows),
            'enemies': sum(r['enemies'] for r in rows),
            'coins': sum(r['coins'] for r in rows),
            'powerups': sum(r['powerups'] for r in rows),
            'hazards': sum(r['hazards'] for r in rows),
        }
    }
    return out


def main():
    report = build_report()
    output = Path(__file__).resolve().parent / 'level_balance_report.json'
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Wrote balance report: {output}')


if __name__ == '__main__':
    main()
