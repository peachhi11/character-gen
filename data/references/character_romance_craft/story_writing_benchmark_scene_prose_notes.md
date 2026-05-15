# Story Writing Benchmark Scene And Prose Notes

## Purpose
This reference distills the useful parts of the Hugging Face dataset:
- `lars1234/story_writing_benchmark` using the `average` config

Use only the English subset for CharacterGen.
Discard the German and Spanish rows for this workflow.

It is useful for:
- `scenario`
- `first_mes`
- scene beginnings
- scene continuations
- atmospheric prose

It is not the right source for:
- `Speech Examples`
- realistic conversational tone shifts
- relationship-specific back-and-forth

## Non-Verbatim Rule
This file is a prose-quality guide, not source text to imitate directly.

Borrow:
- scene pacing
- atmospheric density
- opening efficiency
- continuity habits

Do not let benchmark-summary language surface verbatim in generated scenes.

## Why The English Subset Is Useful
- It contains full stories, scene beginnings, and scene continuations.
- It includes quality scores, so better prose can be filtered from weaker prose.
- The English split is large enough to compare stronger and weaker scene-writing habits.

English subset snapshot:
- `3480` rows
- `1320` `scene_beginning`
- `1320` `scene_continuation`
- `840` `complete`

Quote-heavy scene writing is common in stronger rows:
- high-scoring `scene_beginning` sample quote presence was about `0.98`
- high-scoring `scene_continuation` sample quote presence was about `0.96`
- high-scoring `complete` sample quote presence was about `1.0`

That means strong narrative prose here usually still includes active spoken interaction instead of pure exposition.

## Best Use In CharacterGen

### For `scenario`
- Build pressure around a concrete present-tense situation.
- Prefer scenes with active constraints, not just a premise summary.
- Let setting, stakes, and mood arrive together instead of as separate explanation blocks.

### For `first_mes`
- Open on a specific sensory frame.
- Ground the setting quickly through one or two strong details.
- Introduce the main figure through action, physicality, or a charged observation.
- Move into interaction fast enough that the scene feels live.

## High-Scoring Opening Patterns

### 1. Immediate Atmosphere
Stronger openings start with:
- weather
- light
- sound
- material texture
- motion already underway

Good pattern:
- one or two vivid environmental details
- immediate tie to the viewpoint character’s state or situation

### 2. Character In Motion
Better scene beginnings do not leave the protagonist as a static fact sheet.

They usually:
- stand somewhere specific
- hold or examine something
- approach a door, room, street, or threshold
- react physically before explaining

### 3. Narrowed Focus
The best openings feel selective.

They do not describe the whole world.
They choose:
- one room
- one street
- one threshold
- one charged object
- one immediate tension

### 4. Dialogue Or Near-Dialogue Arrives Early
The stronger samples often bring in:
- direct speech
- a remembered line
- a question
- a challenge
- a spoken interruption

This helps the prose feel active instead of museum-like.

### 5. Setting Is Doing Narrative Work
In stronger rows, setting is not wallpaper.
It reinforces:
- fear
- secrecy
- class pressure
- decay
- ritual
- impending confrontation

## High-Scoring Continuation Patterns

### 1. Continuations Resume With Momentum
They do not restart the story.
They continue from:
- an unresolved plea
- a decision point
- a confrontation already underway
- a danger or revelation already established

### 2. Emotional Carryover Is Visible
Good continuations show what the previous scene cost.

That means:
- hesitation
- altered tone
- tightened focus
- changed trust
- fatigue
- renewed resolve

### 3. They Respect Existing Stakes
The continuation does not flatten the previous tension.
It pays it forward into the next move.

### 4. Action And Reflection Stay Interlocked
The better rows do not freeze into internal monologue.
They let thought exist, but under pressure from:
- dialogue
- movement
- time
- danger
- obligation

## Strong Prose Habits Worth Borrowing
- concrete scene entry instead of abstract setup
- physical nouns over generic mood language
- restrained but specific sensory detail
- spoken interaction inside scene prose
- short threshold transitions
- emotionally loaded objects
- setting pressure fused with character pressure

## Failure Modes In Lower-Scoring Rows

### 1. Generic Grandiosity
Weaker samples often sound like:
- “the world had long since forgotten...”
- “the city was a monument to...”
- broad symbolic framing before anything actually happens

This reads like summary, not scene.

### 2. Placeholder Epicness
Low-scoring prose often leans on:
- invented-proper-noun inflation
- vague tyranny
- generic rebellion
- stock noble heroine framing

The result feels prefabricated.

### 3. Too Much Setup Before Interaction
Some weaker rows spend too long:
- explaining the regime
- explaining the city
- explaining the social order
- describing the protagonist in broad strokes

before the scene actually starts.

### 4. Flat Emotional Texture
Lower rows often describe danger or sorrow in a generic way but do not localize it in:
- body reaction
- speech rhythm
- object focus
- scene choices

### 5. Overwritten Length
The weaker examples tended to run longer on average while doing less with the space.
Longer is not better if the scene does not keep changing state.

## Practical Rules For CharacterGen
- `scenario` should read like a live pressure frame, not a book-jacket summary.
- `first_mes` should enter through place, body, and immediate tension.
- Use atmosphere to sharpen stakes, not to show off vocabulary.
- Prefer one vivid threshold over five broad setting facts.
- Bring in dialogue or a direct social cue early when possible.
- Let objects, weather, sound, or architecture mirror the scene’s emotional pressure.
- Avoid generic “epic” phrasing unless the source setting truly demands it.

## What Not To Borrow Blindly
- the dataset’s genre-default worldbuilding voice
- fantasy-name inflation
- benchmark-style prompt literalism
- long descriptive intros with no live interaction
- any non-English rows for CharacterGen prompt mining

## Recommendation
Use this dataset as a prose-and-scene craft reference for:
- openings
- continuation logic
- atmospheric compression

Do not use it as the main reference for:
- dialogue realism
- romance-specific chemistry
- emotional voice shifts in conversation

For this repo, treat it as an English-only mining source.
