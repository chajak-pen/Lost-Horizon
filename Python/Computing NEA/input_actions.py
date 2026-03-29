import pygame


def action_down(event, keybinds, action):
    return getattr(event, 'type', None) == pygame.KEYDOWN and getattr(event, 'key', None) in keybinds.get(action, ())


def action_pressed(keys, keybinds, action):
    for key in keybinds.get(action, ()):  # pygame key constants
        try:
            if keys[key]:
                return True
        except Exception:
            continue
    return False
