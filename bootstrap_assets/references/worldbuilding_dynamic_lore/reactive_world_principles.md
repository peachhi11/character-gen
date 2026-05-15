# Reactive World Principles

## Purpose
This reference normalizes the useful parts of:
- `reactive_world_lorebook.json`
- `continuation_of__reactive_world__part_2_lorebook.json`

Those source files are conceptually useful, but structurally weak as lorebooks. They are mostly always-on, constant instruction entries with no keys, no selective activation, and no real trigger discipline.

For CharacterGen, treat them as a future runtime and worldbuilding design reference, not as a prompt bundle to inject wholesale.

## Non-Verbatim Rule
This file is a systems-principles layer, not output copy.

Use it to shape:
- world autonomy
- consequence handling
- NPC motion
- delayed causality

Do not surface these principles as direct prose in generated scenes or lore entries.

## What The Source Lorebooks Are Good At
- preserving user agency
- keeping the world active off-screen
- making consequences delayed, uneven, and socially filtered
- treating NPCs as autonomous agents with goals and routines
- keeping information partial, biased, and local
- using memory selectively instead of logging everything
- preserving naming, language, and cultural consistency
- keeping world events larger than the user alone

## What Should Be Tightened
- do not keep these ideas as many tiny constant entries
- do not use lorebook format when the content is really a runtime rule set
- do not make every principle always-on at the same priority in exported lorebooks
- separate global simulation rules from scene-local event entries

## Normalized Design

### 1. User Agency Rules
- Never write dialogue, thoughts, emotions, or decisions for the user.
- Never resolve both sides of an interaction.
- If uncertain, leave the user side open and continue only with NPCs, environment, or consequences.

### 2. World Autonomy
- The world continues when the user is not looking at it.
- NPCs pursue goals, routines, grudges, and obligations independently.
- Resolved scenes should create follow-on motion elsewhere in the setting.

### 3. Consequence Timing
- Consequences do not need to arrive immediately.
- Reactions should depend on who witnessed what, who repeated it, and how distorted the information became.
- Silence, delay, denied access, rumor, retaliation, and changed tone are all valid consequence channels.

### 4. Reputation And Information Spread
- NPCs remember patterns more than isolated incidents.
- Public behavior matters more than private behavior.
- Information should spread unevenly and imperfectly.
- Contradictory accounts are normal and can preserve realism.

### 5. Partial Knowledge
- NPCs should only know what they could plausibly know.
- Hidden motives, plots, and off-screen actions should surface through discovery, rumor, evidence, or confrontation.
- Lore should enter through perspective and implication, not summary exposition.

### 6. NPC Autonomy
- Significant NPCs need their own wants, limits, blind spots, and thresholds.
- Ignored NPCs should keep moving instead of freezing in place.
- NPC success or failure should depend on motive, capacity, timing, and circumstance.

### 7. Pressure Model
- Maintain an unseen pressure layer driven by conflict, secrecy, fatigue, unresolved history, and social risk.
- Rising pressure should change pacing, patience, mistakes, tone, and volatility.
- Pressure should be felt through behavior and atmosphere, never shown as a number.

### 8. Selective Memory
- Only store emotionally significant, symbolic, or identity-defining moments.
- Casual dialogue and routine scene beats should not become permanent memory.
- Stored memory should reappear as changed tone, trust, hesitation, or tenderness, not repeated recap.

### 9. Symbolic Carryover
- Objects, phrases, promises, gestures, injuries, and gifts can acquire lasting emotional meaning.
- Symbols should return when context makes them matter, not on every turn.

### 10. World Scale
- The world should not orbit the user by default.
- Attention depends on status, reputation, visibility, context, and current stakes.
- Background events, unrelated conversations, faction moves, and other storylines can continue without the user.

### 11. Language And Naming
- Dialogue should match the setting's era, class structure, and technology level.
- Accents should be implied through rhythm and vocabulary, not exaggerated spelling.
- New names should follow cultural and regional logic and avoid generic fantasy defaults.
- Once naming patterns exist, preserve them consistently.

### 12. Consistency And Emergent Lore
- Once a fact enters the world, preserve it unless change is explained.
- New lore can emerge during play, but should be framed as local truth, rumor, uncertainty, or developing knowledge until confirmed.
- Contradictions should come from perspective, misinformation, or change over time, not accidental overwrite.

## Best Use In CharacterGen
- future `World Building` tab logic
- future dynamic lore and event systems
- future lorebook export rules that distinguish:
  - global runtime laws
  - relationship state
  - scene events
  - triggerable local lore
- future NPC autonomy and memory-state scripting

## Export Guidance
If these principles are ever converted back into lorebook form:
- keep global runtime laws in one small high-priority rules block
- move memory, naming, and language into separate low-count rule entries
- reserve triggerable entries for places, factions, NPCs, and events
- avoid giant stacks of constant entries with no keys
