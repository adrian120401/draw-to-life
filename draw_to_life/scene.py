"""Geometría y estilos compartidos por la app y el visor descargable."""

from pathlib import Path

SCENE_CSS = (Path(__file__).parent / "web" / "scene.css").read_text(encoding="utf-8")

ICONS = {
    "photo": '<rect x="3" y="3" width="18" height="18" rx="4"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m3 17 5-5 4 4 4-6 5 7"/>',
    "food": '<path d="M12 7c-7-4-11 3-7 10 2 4 4 3 7 3s5 1 7-3c4-7 0-14-7-10Z"/><path d="M12 7V3m0 3c0-4 4-4 5-3-1 3-3 3-5 3Z"/>',
    "heart": '<path d="M20 5c-3-3-6-1-8 1-2-2-5-4-8-1-4 4 1 9 8 15 7-6 12-11 8-15Z"/>',
    "play": '<circle cx="12" cy="12" r="9"/><path d="M7 5c2 4 6 8 12 12M4 13c5-3 10-3 16-2M13 3c-3 5-3 11-1 18"/>',
    "pause": '<path d="M8 5v14M16 5v14"/>',
    "resume": '<path d="m9 5 10 7-10 7Z"/>',
}


def icon(name: str) -> str:
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICONS[name] + '</svg>')


DECORATIONS = '''<div class="playroom-shapes" aria-hidden="true">
<svg class="shapes-wide" viewBox="0 0 1440 1000" preserveAspectRatio="xMidYMid slice">
<path d="M-40 130C80-20 220 55 185 170S25 270-40 215Z" fill="#C7B3EB"/>
<path d="M1240-40c-70 90 20 115 100 100s120 80 160 120V-40Z" fill="#D5C6F2"/>
<path d="m1198 256 15 31 34 5-25 24 6 34-30-16-30 16 6-34-25-24 34-5Z" fill="#F7D88D"/>
<circle cx="245" cy="358" r="16" fill="#F1ADC8"/>
<circle cx="1292" cy="630" r="21" fill="#B79BDC"/>
<path d="M-30 830c150-150 200 30 300 20s100 130 40 180H-30Z" fill="#D2C0EE"/>
<path d="M1190 1060c-130-90-70-200 30-180s120-100 250-50v230Z" fill="#C6B0E6"/>
<path d="m265 740 8 19 21 3-15 14 4 21-18-10-18 10 4-21-15-14 21-3Z" fill="#F7D88D"/>
<path d="m1110 450 5 11 12 2-9 8 2 12-10-6-11 6 2-12-9-8 12-2Z" fill="#F1ADC8"/>
</svg><svg class="shapes-narrow" viewBox="0 0 390 844" preserveAspectRatio="xMidYMid slice">
<path d="M-30 75C30-10 130 5 104 90S14 155-30 130Z" fill="#C7B3EB"/>
<path d="m329 164 8 18 20 3-14 14 3 20-17-9-18 9 4-20-15-14 20-3Z" fill="#F7D88D"/>
<circle cx="48" cy="255" r="9" fill="#F1ADC8"/>
<circle cx="351" cy="595" r="12" fill="#B79BDC"/>
<path d="M-30 773c55-85 90-15 130-9s60 50 45 100H-30Z" fill="#D2C0EE"/>
<path d="M275 880c-45-55-35-104 14-102s47-62 121-31v133Z" fill="#C6B0E6"/>
<path d="m62 655 5 11 12 2-9 8 2 12-10-6-11 6 2-12-9-8 12-2Z" fill="#F7D88D"/>
</svg></div>'''
