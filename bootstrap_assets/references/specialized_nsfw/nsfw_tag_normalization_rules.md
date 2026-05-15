# NSFW Tag Normalization Rules

## Purpose
This reference is for optional adult-only mode work.

Use it to normalize:
- messy source tags
- prompt-reconstruction labels
- duplicate act names
- overlapping dynamic labels

Keep this layer separate from standard grounded generation.

## Non-Verbatim Rule
This file is a normalization guide, not output copy.

Do not surface its examples, canonical labels, or synonym maps verbatim in user-facing text.
Use it only to:
- collapse duplicates
- choose stable labels
- support unique generation downstream

If the model starts printing taxonomy instead of writing, it is using this layer wrong.

## Core Rule
Normalize toward:
- one canonical act label
- one optional dynamic label
- one optional tone/intensity label
- one optional setting or framing label

Do not keep five near-identical synonyms if one canonical label will do.

## Recommended Tag Shape
- `act:*`
- `dynamic:*`
- `tone:*`
- `framing:*`
- `setting:*`
- `body_focus:*`

Example:
- `act:oral_receiving`
- `dynamic:dominance_submission`
- `tone:rough`
- `framing:aftercare`

## Normalization Principles

### 1. Collapse Synonyms
Examples:
- `blowjob`, `bj`, `fellatio`, `sucking cock` -> `act:oral_on_penis`
- `eating out`, `cunnilingus`, `oral on pussy` -> `act:oral_on_vulva`
- `fingering`, `digital penetration` -> `act:fingering`
- `handjob`, `manual stimulation` -> `act:handjob`
- `piv`, `penetrative sex`, `fucking` -> `act:vaginal_penetration`
- `anal`, `butt sex`, `anal intercourse` -> `act:anal_penetration`
- `making out`, `heavy kissing` -> `act:making_out`

### 2. Separate Act From Dynamic
These are not the same:
- `oral sex` is an act
- `dominance` is a dynamic
- `praise kink` is a dynamic/tone
- `rough sex` is a tone/intensity modifier

Do not bury dynamics inside act labels if they can stand alone.

### 3. Separate Act From Tone
Examples:
- `rough blowjob` -> `act:oral_on_penis` + `tone:rough`
- `gentle sex` -> `act:vaginal_penetration` + `tone:gentle`
- `desperate kissing` -> `act:making_out` + `tone:desperate`

### 4. Separate Framing From Mechanics
Examples:
- `shower sex` -> `setting:shower` plus the actual act tag
- `office sex` -> `setting:office` plus the actual act tag
- `only one bed` -> `framing:forced_proximity_bedsharing`

### 5. Prefer Human-Readable Canonical Labels
Good:
- `act:oral_on_penis`
- `dynamic:orgasm_control`
- `framing:public_risk`

Less good:
- `act:fellatio_only`
- `dyn:domsub_lvl2`

## Recommended Canonical Buckets

### Acts
- `act:kissing`
- `act:making_out`
- `act:handjob`
- `act:fingering`
- `act:oral_on_penis`
- `act:oral_on_vulva`
- `act:vaginal_penetration`
- `act:anal_penetration`
- `act:grinding`
- `act:thigh_riding`
- `act:mutual_masturbation`
- `act:sex_toy_use`

### Dynamics
- `dynamic:dominance_submission`
- `dynamic:praise`
- `dynamic:degradation`
- `dynamic:service`
- `dynamic:brat_tamer`
- `dynamic:caregiver`
- `dynamic:orgasm_control`
- `dynamic:possessive_attention`
- `dynamic:primal`
- `dynamic:voyeurism`
- `dynamic:exhibitionism`

### Tone And Intensity
- `tone:gentle`
- `tone:tender`
- `tone:teasing`
- `tone:desperate`
- `tone:possessive`
- `tone:rough`
- `tone:playful`
- `tone:reverent`

### Framing
- `framing:aftercare`
- `framing:first_time`
- `framing:reunion`
- `framing:public_risk`
- `framing:forbidden`
- `framing:ritualized`
- `framing:power_exchange`

### Setting
- `setting:bedroom`
- `setting:bathroom`
- `setting:shower`
- `setting:office`
- `setting:car`
- `setting:outdoors`

## Duplicate Control
- Keep one canonical tag per concept.
- If source data has both `bj` and `blowjob`, store only the canonical form.
- If source data has both `rough sex` and `hard fucking`, normalize to one tone label plus one act label.

## Exclusions
Do not normalize taboo, illegal, minor-involving, coercive, or non-consensual content into the active optional library unless the project later creates an explicitly separate exclusion-reviewed layer for them.

For this layer:
- keep it adult-only
- keep it consensual
- keep it optional
