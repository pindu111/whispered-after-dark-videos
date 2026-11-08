# Whispered After Dark — daily story guide

Channel: **Whispered After Dark** — short, original horror stories told in the dark. One new story every night.

## The story
- **Original only.** Never retell a creepypasta, film, book, Reddit post or urban legend someone else wrote. Never reuse a premise, twist or title already in `stories/` — read them all before writing.
- 7–10 caption cards, each one sentence (max ~22 words). Total narration about 25–45 seconds.
- Card 1 is the hook: an ordinary, specific domestic detail that is slightly wrong.
- Build quietly. The last card is a short twist (≤ 8 words) that recolours everything before it.
- First person, plain modern English, no gore, no real people or places, nothing sexual, nothing involving harm to children. Unsettling, not graphic.
- Vary the settings week to week: home, work, school, road trips, phones, neighbours, hotels, camping, the sea, childhood memories, technology.

## Scenes (one per card)
`house` `hallway` `table` `window` `forest` `door` `note` `dark`
Pick the scene that fits each line; use `dark` for the beat right before the twist or the twist itself. Avoid the same scene on two cards in a row.

## Story file — `stories/NNN-slug.json`
```json
{
  "title": "Two to Four Words",
  "title_scene": "house",
  "cards": [{"text": "...", "scene": "table"}],
  "outro": "Follow for a new story every night.",
  "youtube": {
    "title": "Hooky title under 70 chars… #shorts #scarystories",
    "description": "First two lines of the story as a teaser.\n\nA new original scary story every night on Whispered After Dark.\n\n#scarystories #horror #creepy #shorts",
    "tags": ["scary stories", "horror", "creepy", "short horror story", "shorts", "whispered after dark"]
  }
}
```
NNN is the next number after the highest in `stories/`.
