import pygame


def draw_tab_button(surface, rect, text, font, active=False):
    fill = (64, 100, 148) if active else (30, 52, 86)
    border = (170, 220, 255) if active else (90, 130, 185)
    pygame.draw.rect(surface, fill, rect, border_radius=9)
    pygame.draw.rect(surface, border, rect, 2, border_radius=9)
    label = font.render(text, True, (245, 248, 255) if active else (205, 220, 240))
    surface.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))


def draw_card_panel(surface, rect):
    pygame.draw.rect(surface, (16, 28, 48, 205), rect, border_radius=12)
    pygame.draw.rect(surface, (100, 155, 225), rect, 2, border_radius=12)


def wrap_text(font, text, max_width):
    if max_width <= 0:
        return [text]
    words = str(text or "").split()
    if not words:
        return [""]

    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def fit_text(font, text, max_width):
    text = str(text or "")
    if max_width <= 0:
        return ""
    if font.size(text)[0] <= max_width:
        return text
    short = text
    while len(short) > 1:
        short = short[:-1]
        candidate = short + "..."
        if font.size(candidate)[0] <= max_width:
            return candidate
    return "..."


def draw_wrapped_text(surface, font, text, color, rect, line_gap=4, align="left", max_lines=None):
    x, y, w, _ = rect
    lines = wrap_text(font, text, w)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = fit_text(font, lines[-1], w)

    cursor_y = y
    for line in lines:
        surf = font.render(line, True, color)
        if align == "center":
            draw_x = x + (w - surf.get_width()) // 2
        elif align == "right":
            draw_x = x + w - surf.get_width()
        else:
            draw_x = x
        surface.blit(surf, (draw_x, cursor_y))
        cursor_y += surf.get_height() + line_gap
    return cursor_y
