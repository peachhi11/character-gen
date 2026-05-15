# Grounded BDSM Source Routing

## Purpose
This note routes the current grounded BDSM source batch into CharacterGen's existing and planned module structure.

Use it when deciding:
- which files to author next
- which bundle each source should feed
- which sources are primary versus secondary support

## Core Rule
Do not ingest these papers as raw prose.
Distill them into behavior, relationship logic, repair logic, safety logic, and role motivation.

## Highest-Value Source Set

### Primary keepers
- `Oh, Are You Just Kinky in Bed?`
- `To know thyself` dominant-motivation thesis
- `Comforting, Reassuring, and...Hot`
- Turley qualitative / phenomenological thesis
- `Perks, problems, and the people who play`

### Selective support
- `BDSM, becoming and the flows of desire`

### Pending direct review
- PsycNet `2015-14979-005`
- PsycNet `2027-52442-001`
- PMC `10902275`
- PMC `9825129`
- ProQuest dissertation

## Route Map

### `data/references/character_psychology`
Use for:
- role meaning
- stigma and identity integration
- emotional regulation
- shame and concealment
- benefits, risks, and misreadings of BDSM roles

Best source feeds:
- `Oh, Are You Just Kinky in Bed?`
- `To know thyself`
- `Perks, problems, and the people who play`

Planned outputs:
- `bdsm_identity_stigma_and_emotional_regulation.md`
- `power_exchange_identity_and_role_meaning.md`
- `bdsm_role_benefits_risks_and_misreadings.md`

### `data/references/character_romance_craft`
Use for:
- care
- trust
- attunement
- negotiation
- erotic safety
- belonging and discovery

Best source feeds:
- `Oh, Are You Just Kinky in Bed?`
- `Comforting, Reassuring, and...Hot`
- Turley thesis
- `BDSM, becoming and the flows of desire`

Planned outputs:
- `care_trust_and_attunement_in_power_exchange.md`
- `sensory_safety_reassurance_and_erotic_trust.md`
- `desire_discovery_and_belonging_in_bdsm.md`

### `data/references/intimacy_archetypes`
Use for:
- grounded dominant motivation
- stewardship
- surrender logic
- attentiveness
- responsibility

Best source feeds:
- `To know thyself`
- Turley thesis
- `Perks, problems, and the people who play`

Planned outputs:
- `dominant_motivations_and_stewardship.md`
- `submission_stewardship_and_surrender_logic.md`

### `data/references/explicit_dialogue`
Use for:
- reassurance language
- negotiation language
- aftercare language
- consent-forward erotic communication

Best source feeds:
- `Comforting, Reassuring, and...Hot`
- Turley thesis
- `Oh, Are You Just Kinky in Bed?`

Planned outputs:
- `reassurance_negotiation_and_aftercare_language.md`

### `data/references/prompt_validation`
Use for:
- anti-flattening rules
- source hygiene
- filtering out cartoon power dynamics
- promotion criteria for BDSM material

Best source feeds:
- `Oh, Are You Just Kinky in Bed?`
- `Perks, problems, and the people who play`
- the broader grounded-source batch as a whole

Planned outputs:
- `bdsm_source_quality_and_anti-flattening_rules.md`

## Priority Order
Author these first:
1. `character_romance_craft/care_trust_and_attunement_in_power_exchange.md`
2. `intimacy_archetypes/dominant_motivations_and_stewardship.md`
3. `character_romance_craft/sensory_safety_reassurance_and_erotic_trust.md`
4. `explicit_dialogue/reassurance_negotiation_and_aftercare_language.md`
5. `prompt_validation/bdsm_source_quality_and_anti-flattening_rules.md`

## Why This Order
This order closes the biggest remaining CharacterGen gaps:
- how power exchange can feel caring rather than cartoonishly harsh
- how dominant/submissive roles differ in motivation and attention
- how safety, reassurance, and eroticism coexist
- how characters actually talk during negotiation, reassurance, and aftercare
- how to keep weak BDSM source material out of the runtime stack
