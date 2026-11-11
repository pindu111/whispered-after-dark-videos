# Whispered After Dark — daily story guide

Channel: **Whispered After Dark** — short, original horror stories told in the dark. One new story every night.

**The goal of every story is engaged views: viewers who don't swipe in the first second, watch to the very end, and rewatch.** Every rule below serves that.

## Hard rules
- **Original only.** Never retell a creepypasta, film, book, Reddit post or urban legend someone else wrote. Never reuse a premise, twist or title already in `stories/`. Read them all before writing.
- First person, plain modern English, no gore, no real people or places, nothing sexual, nothing involving harm to children. Unsettling, not graphic.
- Vary the settings: home, work, night shifts, school, road trips, phones, neighbours, hotels, camping, the sea, childhood memories, technology. Don't use the same setting as either of the last 3 stories.

## Structure (7–9 cards, 25–35 seconds of narration)
1. **Card 1, the hook (≤ 8 words, readable in one second).** It's the first thing seen and heard; there is no title card. It must be concrete and *already wrong*, and raise a question the viewer needs answered. Never open with setup, dates, names or "so...". Bad: "Wet footprints walk out of the sea and stop at my door." (11 words, too slow). Good: "Footprints come out of the sea. Mine."
   **Rotate the hook type** so we learn which keeps viewers. Use the type that has been used least recently (check `hook_type` in earlier stories) and record it as `"hook_type"` in the story file:
   - `warning`: talks to the viewer. "Don't answer if your phone rings at 3:14."
   - `rule`: a creepy rule. "Never let the night nurse see you awake."
   - `confession`: something the narrator did. "I locked my sister out. She's still knocking."
   - `impossible`: a plain impossible fact. "My reflection blinked first."
   - `question`: a direct question. "Have you ever counted your stairs at night?"
2. **Card 2 makes the hook worse,** usually by adding the one fact that makes it impossible ("It has only ever been the two of us."). By the end of card 2 the viewer must know the premise.
3. **Middle cards escalate.** Each card is scarier than the one before (odd → unsettling → wrong → terrifying). Every card must either raise the stakes or open a new question. If a card only explains or describes, cut it.
4. **Second-to-last card is the quiet beat:** a pause or discovery that sets up the twist ("This morning, there was a note on my plate.").
5. **Last card, the twist (≤ 8 words).** It reframes everything before it so the viewer wants to rewatch. It must be *set up* by earlier details (fair, not random) and must not need explaining. Nothing comes after it: the video ends on the twist.
6. **Loop bonus (when it fits naturally):** a last line that sends the viewer back to the first line makes rewatches seamless.

## Line craft
- One sentence per card, ideally 6–16 words, never more than 20. Each card is on screen for ~3 seconds.
- Concrete sensory details (a chair scraping at 3am), never vague ones (a strange noise).
- No adjectives that tell the viewer how to feel ("creepy", "terrifying", "eerie"). Show the thing and let them feel it.
- No backstory, no explaining the monster, no "I later found out...". Leave the gap for the viewer's imagination.
- Use dialogue sparingly. One short quoted line is often the scariest card.
- Read every card aloud in your head: it must sound natural spoken by a narrator.

## Writing process (do this every time)
1. Brainstorm 5 different premises in one line each. Pick the one with the strongest hook *and* the strongest twist that's set up by the hook.
2. Write 3 alternative hooks for it and keep the one that most makes you need card 2.
3. Write the story, then score it 1–5 on: hook strength, escalation, every-card-earns-its-place, twist surprise, twist fairness, rewatch pull. Rewrite any card that drags a score below 4. Cut any card you can remove without losing anything.
4. Write the YouTube title last: a curiosity gap in under 60 characters that hints at the premise without spoiling the twist (e.g. "My Mum Always Sets a Third Plate…"). Never reuse the twist in the title or description.

## Scenes (one per card)
`house` `hallway` `table` `window` `forest` `door` `note` `dark`
Pick the scene that fits each line; use `dark` for the beat right before the twist or the twist itself. Never use the same scene on two cards in a row, so the picture changes on every line.

## Photos (one real photo per card, from Unsplash)
Every card gets a real photo; the drawn `scene` stays as a fallback if a photo download ever fails.
- For each card, search Unsplash (`search_photos`, orientation `portrait`, plus `none`, content_filter `high`, per_page 5) with a short concrete query for what the line shows, e.g. "car dashboard night", "empty hotel corridor", "foggy forest path". Keep queries to 2–4 words.
- Pick the result that best matches the line *and* is dark, moody and uncluttered (night, fog, empty rooms, shadows). Skip bright daytime, smiling people, recognisable landmarks, brand logos, text, and anything with children.
- Faces are fine only as shadowy silhouettes. Never use a clear, identifiable face.
- Don't use the same photo twice in one video or a photo already used in any earlier story (check the `photo_id`s in `stories/`).
- For each chosen photo call `download_asset` with its id (Unsplash requires this). Store its returned `url` as `photo`, the id as `photo_id`, and the photographer's `user.name` as `photo_credit` on the card.
- The video maker darkens and colour-grades every photo automatically, so pick for subject and composition, not exposure.

## Story file: `stories/NNN-slug.json`
```json
{
  "title": "Two to Four Words",
  "hook_type": "warning",
  "cards": [{"text": "...", "scene": "table", "photo": "https://images.unsplash.com/photo-...", "photo_id": "abc123", "photo_credit": "Photographer Name"}],
  "youtube": {
    "title": "Curiosity-gap title under 60 chars… #shorts #scarystories",
    "description": "The hook line and card 2 as a teaser.\n\nA new original scary story every night on Whispered After Dark.\n\nPhotos: Name One, Name Two, Name Three on Unsplash\n\n#scarystories #horror #creepy #shorts",
    "tags": ["scary stories", "horror", "creepy", "short horror story", "shorts", "whispered after dark"]
  }
}
```
NNN is the next number after the highest in `stories/`. Add 1–2 extra tags that fit the story's setting (e.g. "hotel horror").
