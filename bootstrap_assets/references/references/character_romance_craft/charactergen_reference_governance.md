# CharacterGen Reference Governance

## Canonical Target
CharacterGen is the primary destination for relationship, psychology, dialogue, and scenario reference work.

Its taxonomy is canonical.
Its runtime needs decide what gets promoted.
Its reference bundles are the final home for distilled guidance.

## Non-Verbatim Rule
This is a governance document, not prompt output copy.

Use it to control:
- promotion
- structure
- bundle ownership
- source hygiene

Do not let its wording bleed directly into generated content.

## Helper Layer Rule
`novelist-ai` is a helper layer, not the destination schema.

Use helper systems like `novelist-ai` to:
- mine source material
- deduplicate noisy prompt dumps
- normalize tone and terminology
- rewrite weak source phrasing into cleaner internal guidance
- pressure-test whether a reference is actually useful

Do not let helper systems define CharacterGen's final structure.

## Promotion Pipeline
Use this order when bringing in new source material:
1. gather raw source material
2. distill it with helper tooling if needed
3. map the distilled result into CharacterGen's own reference taxonomy
4. promote only the cleaned output into CharacterGen bundles

Raw source should not be pasted directly into CharacterGen just because it is large, popular, or emotionally on-theme.

## What CharacterGen Owns
CharacterGen should own:
- category boundaries
- runtime-facing naming
- what counts as psychology versus trope versus intimacy versus validation
- the grounded behavior rules that steer generation quality

If an outside reference is useful but does not fit cleanly, rewrite it until it does.

## Quality Standard
Prefer references that improve:
- behavior under pressure
- relationship logic
- emotional range
- nonverbal intimacy
- support and repair dynamics
- scenario pressure

Demote or quarantine sources that mainly contribute:
- filler dialogue
- repetitive fluff
- kink catalogs without character logic
- low-quality erotic phrasing
- route labels without usable behavior

## Practical Rule
Think of `novelist-ai` as a refinery.
Think of CharacterGen as the system of record.

If the two disagree on structure, CharacterGen wins.
