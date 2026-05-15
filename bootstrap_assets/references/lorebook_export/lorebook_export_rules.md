# Lorebook Export Rules and Validation

## Purpose
This reference folds in the most useful structural rules from:
- `universal-lorebook-creator/README.md`
- `universal-lorebook-creator/lorebook_creator_v2.md`
- the useful tooling lessons from `awesome-regex`

Use it as the future design reference for CharacterGen lorebook export, world-building entry generation, and validation.

## Non-Verbatim Rule
This file should guide export structure, not appear in generated lore text verbatim.

Use it to shape:
- entry granularity
- taxonomy
- validation
- trigger hygiene

If output starts sounding like export rules instead of actual lore content, rewrite it.

## Core Rule
Generate structured lore entries, not blobs.

Each entry should represent:
- one concept
- one entity
- one rule
- one scene event
- one relationship node

Do not combine unrelated concepts into a single catch-all entry.

## Strong Entry Taxonomy
Useful export categories:
- world rules and mechanics
- characters
- relationships
- locations
- items and objects
- factions and organizations
- events and history
- concepts and terms
- protocols and procedures
- active scenes or temporary states

## Three-Decision Framework
Every future lore entry should answer:
1. what type is it?
2. where should it inject?
3. how important is it?

### 1. Type
- constant rule
- normal keyword-triggered entry
- temporary scene event

### 2. Position
Useful future mapping:
- before character definitions
- after character definitions
- after examples
- in-chat depth layer
- author-note layer

### 3. Priority
Use broad tiers, not everything at the same weight:
- nuclear
- critical
- high
- standard
- background
- flavor

The biggest lorebook mistake is flattening all entries to the same priority.

## Keyword Rules
Good keywords are:
- specific
- natural
- short
- disambiguating

Good practice:
- 2 to 5 keywords per entry
- include natural variations
- include titles or possessives when relevant
- avoid generic trash like `house`, `sword`, `city`, `the`

## Recursion Rules
Recursion should follow entity type.

Usually:
- locations can trigger NPCs or items inside them
- organizations can trigger member entries
- characters should often terminate recursion
- items should often terminate recursion
- hard rules should terminate recursion

The goal is useful chaining, not loops.

## Scene Event Rules
Temporary events should have:
- short content
- clear trigger conditions
- short lifetime / sticky duration
- lower priority than core canon unless critical

Good examples:
- weather shift
- injury state
- combat state
- active argument
- temporary investigation
- party atmosphere

## Content Rule
Entries should be compressed, vivid, and functional.

Good entry content includes:
- role
- defining traits
- relationship hooks
- location or organizational function
- sensory cue when useful
- one or two recursive mentions if needed

## Validation Rules for Future Export
Before future lorebook export, validate:
- one concept per entry
- valid structured fields present
- keyword count in range
- keywords are not overly generic
- recursion flags match entity type
- priorities are distributed
- constant entries are limited
- sticky durations only used when justified
- scene events are temporary, not permanent canon

## Trigger Hygiene
The strongest lesson from both lorebook references and regex tooling is trigger hygiene.

That means:
- normalize casing
- test singular/plural/title variations
- avoid accidental overlap
- avoid broad keywords that fire constantly
- prefer deliberate keyword chains over messy trigger spread

## Regex and Validation Tooling Notes
The `awesome-regex` repo is not content to import. It is useful as a support map for:
- JavaScript regex docs
- regex testing tools
- regex visualization/debugging

Practical future use:
- validate tags
- normalize trigger patterns
- catch malformed keys
- test word-boundary logic before shipping export validators

Useful external helpers noted there:
- `regex101`
- `RegExr`
- MDN JavaScript `RegExp` docs
- JavaScript regex guides and cheatsheets

## What to Avoid
- giant multipurpose entries
- generic keywords
- every entry at one priority
- overusing constant entries
- scene events with no expiry
- recursion everywhere
- lore that reads like a wall of exposition instead of a triggerable unit

## CharacterGen Takeaway
Future lorebook export should be:
- category-based
- trigger-safe
- recursion-aware
- priority-aware
- testable

The goal is not just “export JSON.”
The goal is exportable lore that activates cleanly, survives token pressure, and supports actual roleplay flow.
