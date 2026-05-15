# DeepDialogue Emotion Domain Testing Note

## Purpose
This reference distills the useful testing logic from:
- `DeepDialogue: A Multi-Turn Emotionally-Rich Spoken Dialogue Dataset`

Use it as a prompt-testing and dialogue-range note for CharacterGen.

It is most useful for:
- `Speech Examples`
- future multi-turn dialogue validation
- emotional range checks
- domain-aware tone testing

It is not a realism gold standard.
It is a synthetic but structured emotional-dialogue source.

## Non-Verbatim Rule
This file should guide testing and range coverage, not be echoed as prompt prose.

Borrow:
- emotion spread
- transition plausibility
- domain variety

Do not let evaluation-note language appear directly in generated dialogue.

## Most Useful Source Components
- `41 domains`
  - concrete and abstract conversation settings
- `20 emotions`
  - basic, social, and epistemic emotions
- `3-10 turns`
  - enough depth to test short emotional progression
- `emotion-domain mappings`
  - some emotions fit some domains better than others
- `emotion transition graph`
  - emotional shifts should feel plausible, not random

## What CharacterGen Should Borrow

### 1. Emotion Coverage Should Be Wide
Dialogue testing should not collapse into:
- neutral
- horny
- angry

It should also cover:
- curiosity
- embarrassment
- gratitude
- confusion
- pride
- disappointment
- fear
- tenderness
- jealousy
- hope

### 2. Emotions Should Match Domain Pressure
The same emotional line reads differently depending on context.

Test whether the generated voice adapts to:
- everyday domains
- social domains
- conflict domains
- romance and attraction domains
- knowledge or work domains

Practical rule:
- concrete scene setups usually produce better dialogue than vague abstract setups

### 3. Emotional Shifts Should Feel Adjacent
Useful progression testing asks whether the output moves in believable steps.

Good examples:
- curiosity -> surprise -> excitement
- frustration -> disappointment -> anger
- caution -> trust -> tenderness
- embarrassment -> defensiveness -> honesty

Bad examples:
- flat repetition of the same emotion
- wild jumps without pressure or transition
- instant intimacy without prior emotional movement

### 4. Short Turns Still Need Character
DeepDialogue constrains turns to brief conversational length.

That is useful for CharacterGen because:
- `Speech Examples` should feel line-level and playable
- short lines still need:
  - voice
  - subtext
  - emotional specificity
  - distinct rhythm

## Practical Testing Use

### For `Speech Examples`
Check whether the generated set spans:
- soft / warm
- embarrassed / flustered
- jealous / possessive
- angry / sharp
- emotionally exposed
- playful / teasing
- sexually charged
- public-mask voice
- private softened voice

### For future multi-turn tests
Check whether:
- the tone evolves instead of resetting each turn
- the emotion remains intelligible under pressure
- the character still sounds like themselves while shifting moods
- longer exchanges do not flatten into generic support-chat language

### For scenario prompts
Prefer concrete pressure over abstract thematic framing when testing dialogue quality.

Examples:
- better:
  - missed train after a fight
  - waiting outside the locker room
  - seeing an ex at the party
  - trying to keep calm in a car after bad news
- weaker:
  - a conversation about life
  - a discussion about truth
  - a talk about philosophy and feelings

## What Not To Overclaim
- do not treat the dataset as natural human dialogue
- do not use it as the main source for romance chemistry
- do not use it as proof that a generated conversation is realistic just because the emotional arc is coherent
- do not copy its synthetic brevity into places where CharacterGen needs richer scene pressure

## CharacterGen Takeaway
DeepDialogue is best used as:
- an emotional coverage source
- an emotion-transition testing source
- a domain-vs-tone validation source

It pairs well with:
- `roleplay_bench_validation_reference.md`
- `grounded_explicit_dialogue.md`
- `story_writing_benchmark_scene_prose_notes.md`

It should support testing and calibration, not replace more grounded relationship or prose references.
