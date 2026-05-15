# Roleplay Bench Validation Reference

## Purpose
This reference distills the useful validation logic from:
- `lazyweasel/roleplay-bench`

Use it as an internal quality-check note for CharacterGen prompt testing, especially for:
- `first_mes`
- runtime guardrails
- future dynamic-lore behavior
- adversarial live prompt cases

It is not a prose-style source.
It is a validation-and-failure-mode source.

## Non-Verbatim Rule
This file is a rubric layer, not output copy.

Use it to:
- test openings
- catch drift
- enforce agency and continuity

Do not surface its evaluative wording directly in user-facing generation.

## Most Useful Source Components
- `seeds`
  - structured roleplay setups
  - opening messages
  - initial user turns
  - evaluation focuses
- `adversarial_seeds`
  - deliberate traps for agency, continuity, POV, and instruction drift
- `rubric`
  - explicit roleplay quality dimensions

## Core Validation Priorities

### 1. Instruction Adherence
- Follow the declared runtime contract even under pressure.
- Do not lose important constraints when the scene gets emotional, intimate, or fast-moving.
- Preserve hard rules such as POV lock, user boundary, and response boundary.

### 2. Agency Respect
- Never write the user's internal state.
- Never resolve the user's next action.
- Do not make the user consent, withdraw, react physically, or emote unless they explicitly did so.
- When the user creates an opening and waits, let the character react without stealing the rest of the exchange.

### 3. Character Consistency
- The generated character should keep:
  - core temperament
  - speech rhythm
  - boundaries
  - habits
  - relational logic
- Stress should reveal the character, not replace them.

### 4. POV And Tense Consistency
- Maintain the declared point of view.
- Do not drift into omniscient narration.
- Do not switch between scene mode, summary mode, and meta-instruction voice mid-output.

### 5. Continuity And Context Integration
- Preserve already introduced facts.
- Resolve contradictions intelligently instead of flattening them.
- When a challenge introduces conflicting evidence, the character should engage with it instead of ignoring it or instantly yielding.

### 6. Anti-Sycophancy
- The generated character should not always validate the user automatically.
- Pushback, skepticism, restraint, and disagreement are often signs of stronger roleplay.
- Being warm is not the same as being compliant.

### 7. Narrative Momentum
- If the user goes passive, the scene should not stall into decorative prose.
- The character, world, or pressure system should move the interaction forward without hijacking user agency.

### 8. Subtext And Earned Intimacy
- Attraction should not always be named directly.
- Keep emotionally charged scenes from collapsing into on-the-nose explanation.
- Let tension live in:
  - pauses
  - gesture
  - proximity
  - implication
  - restraint

## Frequent Failure Modes Worth Testing
- agency violation
- POV or tense violation
- system prompt detail loss
- contradictory context resolution failure
- narrative stagnation under passive user turns
- character flattening under pressure
- genre instability
- over-explicit subtext

## Practical Use In CharacterGen

### For prompt cases
Create cases that intentionally test:
- user touch or eye-contact bait
- contradictory lore or historical detail
- passive or non-committal user replies
- scenes where the model is tempted to over-explain attraction

### For live validation
Ask:
- Did the opening keep user agency intact?
- Did the character still sound like themselves?
- Did the scene keep moving without taking over the user?
- Did the prose preserve subtext instead of explaining everything?

## Recommendation
Use this reference to guide:
- new live prompt-test cases
- future validator heuristics
- future dynamic-lore runtime checks

It pairs especially well with:
- `grounded_pov_lock_and_scene_flow.md`
- `reactive_world_principles.md`
- `safe_sandbox_brain_scripts.md`
