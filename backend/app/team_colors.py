import colorsys

PALETTE = ['#00dff2', '#ff6b8a', '#a78bfa', '#6ee787', '#ffb454', '#5b9dff', '#f583db', '#e5e85b']


def next_team_color(used):
    used = {color.lower() for color in used}
    for color in PALETTE:
        if color not in used:
            return color
    for index in range(100000):
        rgb = colorsys.hsv_to_rgb((index * 0.61803398875) % 1, 0.55 + (index % 3) * 0.1, 0.95)
        color = '#' + ''.join(f'{round(channel * 255):02x}' for channel in rgb)
        if color not in used:
            return color
    raise ValueError('No unused team color available')
