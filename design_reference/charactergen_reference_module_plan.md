# CharacterGen Reference Module Plan

## Purpose
This is the working module plan for turning clustered romance, psychology, dialogue, and scenario source material into CharacterGen-native reference files.

This is not a generic writing outline.
It is a CharacterGen implementation map.

The governing rule is:
- CharacterGen is the primary target
- `novelist-ai` is a helper layer for distillation, cleanup, normalization, and output-checking

## Planning Constraint
CharacterGen currently loads reference material through these runtime bundles:
- `character_psychology_reference`
- `character_romance_craft_reference`
- `setting_scaffolds_reference`
- `romance_reference`
- `explicit_dialogue_reference`
- `prompt_validation_reference`
- plus the existing intimacy, kink, seduction, lorebook, POV, and specialized NSFW bundles

That means there are two valid implementation tracks:

1. `Phase 1: no app-code changes`
   Map new material into the existing buckets and file-load path.

2. `Phase 2: schema expansion`
   Add new buckets and prompt tags for cleaner routing once the content proves stable.

## Recommended Approach
Use `Phase 1` first.

Why:
- it is compatible with the current app immediately
- it avoids changing bundle-loading code before the taxonomy settles
- it lets us refine source material inside CharacterGen using real prompts before committing to more tags

After the files stabilize, promote the strongest clusters into `Phase 2` dedicated modules.

## Phase 1: CharacterGen-Ready Mapping

### 1. `data/references/character_psychology`
Use this bucket for emotional logic, attachment, avoidance, confession resistance, and behavior under pressure.

Planned files:
- `attachment_under_stress_and_affection_avoidance.md`
  Covers uncomfortable-with-affection logic, avoidant/anxious reactions, love with low affection fluency.
- `confession_resistance_and_fear_of_reciprocity.md`
  Covers reasons for holding back, fear of ruining the relationship, timing resistance, emotional inhibition.
- `heartbreak_and_abandonment_response_patterns.md`
  Covers breakup aftermath, perceived rejection, self-protective shutdown, memory loops, grief posture.

Source clusters routed here:
- `uncomfortable_with_affection`
- `reasons_for_holding_back`
- `heartbreak_aftermath`

### 2. `data/references/character_romance_craft`
Use this bucket for relationship progression, intimacy logic, repair, emotional pacing, and broad character-route craft.

Planned files:
- `relationship_milestones_and_progression_logic.md`
  Covers commitment milestones, pacing, escalation, and relationship-stage transitions.
- `everyday_love_and_nonsexual_intimacy.md`
  Covers subtle acts of love, domestic affection, nonsexual intimacy, and ordinary tenderness.
- `permission_pacing_and_trust_building.md`
  Covers asking for permission, physical pacing, trust calibration, and consent-shaped intimacy.
- `confession_scene_logic_and_emotional_turns.md`
  Covers what makes confessions land, rupture-to-confession pivots, goodbye confessions, reciprocity dynamics.

Source clusters routed here:
- `relationship_milestones`
- `everyday_love_behaviors`
- `subtle_acts_of_love`
- `permission_and_pacing`
- `physical_affection_nonsexual`
- `nonsexual_intimacy`
- `goodbye_confession`
- `confession_reactions`

### 3. `data/references/explicit_dialogue`
Use this bucket for line-shape patterns and dialogue tone, not for psychology theory.

Planned files:
- `awkward_grumpy_and_restrained_affection_dialogue.md`
  Covers grumpy affection, awkward sweetness, reluctant warmth, emotionally unpracticed tenderness.
- `confession_dialogue_patterns.md`
  Covers awkward confession, drunk confession, angry confession, quiet confession, delayed reciprocity.
- `hurt_comfort_and_protective_dialogue.md`
  Covers reassurance, grounding, caretaking language, protective dialogue, safety language.
- `sleepy_domestic_and_soft_intimacy_dialogue.md`
  Covers sleepy lines, domestic closeness, low-intensity tenderness, at-home relationship texture.

Source clusters routed here:
- `grumpy_affection`
- `awkward_confession`
- `drunk_confession`
- `angry_confession`
- `confession_reactions`
- `hurt_comfort_dialogue`
- `caregiving_actions`
- `comforting_the_caretaker`
- `protective_dialogue`
- `sleepy_dialogue`

### 4. `data/references/romance_tropes`
Use this bucket for reusable route engines and trope logic, not giant prompt dumps.

Planned files:
- `friends_to_lovers_route_engines.md`
  Covers best friends, childhood friends, roommates, flirty friends, slow-burn familiarity routes.
- `enemies_to_lovers_route_engines.md`
  Covers enemies to lovers, reluctant allies, exes, rivalry, mistrust-to-intimacy structures.
- `forced_proximity_route_engines.md`
  Covers isolation traps, one-room pressure, cohabitation stress, and spatially accelerated intimacy routes.
- `structured_relationship_formats.md`
  Covers fake dating, secret relationship, forbidden romance, friends with benefits, second chance.
- `poly_and_complex_relationship_formats.md`
  Covers OT3/poly structures, love triangles, multi-partner communication and stability logic.

Source clusters routed here:
- `best_friends_to_lovers`
- `childhood_friends_to_lovers`
- `roommates_to_lovers`
- `coworkers_to_lovers`
- `neighbors_to_lovers`
- `fake_dating_to_real`
- `friends_with_benefits_to_lovers`
- `enemies_to_lovers`
- `reluctant_allies_to_lovers`
- `forced_proximity`
- `only_one_bed`
- `isolation_trap`
- `exes_to_lovers`
- `second_chance_romance`
- `forbidden_romance`
- `secret_relationship`
- `poly_ot3`
- `love_triangle`

### 5. `data/references/setting_scaffolds`
Use this bucket for scene generators, event pressure, and first-meeting engines.

Planned files:
- `meet_cute_meet_ugly_and_chaotic_intro_engines.md`
  Covers charming first meetings, bad first impressions, and chaos-bonding setups.
- `date_structures_and_date_mishap_engines.md`
  Covers first dates, blind dates, wrong-place/wrong-time failures, interruptions, weather, logistics.
- `relationship_transition_event_scaffolds.md`
  Covers moving in, meeting the family, getting caught, proposal, wedding, honeymoon, parenthood.
- `activity_scene_bank.md`
  Covers museum, carnival, road trip, movie night, rain scenes, public transport, bar talk, cooking.

Source clusters routed here:
- `meet_cute`
- `meet_ugly`
- `meet_chaotic`
- `first_date`
- `date_mishaps`
- `secret_relationship`
- `meeting_the_family`
- `moving_in_together`
- `proposal_wedding_marriage`
- `pregnancy_parenthood`
- `date_activities`
- `museum_date`
- `carnival_fair`
- `movie_night`
- `cooking_together`
- `rain_scene`
- `public_transport`
- `bar_conversation`
- `road_trip`

### 6. `data/references/prompt_validation`
Use this bucket for quality rules that stop prompt-dump noise from degrading outputs.

Planned files:
- `romance_reference_deduplication_rules.md`
  Rules for merging duplicate prompt sets, collapsing variants, and stripping filler.
- `dialogue_quality_filters.md`
  Rules for avoiding generic fluff, repeated line shapes, low-value heartbreak one-liners, and flat trope labels.
- `character_logic_promotion_criteria.md`
  Rules for what gets promoted into CharacterGen: behavior under pressure, route logic, nonverbal intimacy, support and repair.

Source clusters routed here:
- cluster-level dedupe logic
- anti-filler logic
- promotion criteria from the governance layer

### 7. `design_reference` or lookup-only storage
Do not load these directly into runtime prompts unless they get distilled first.

Planned files:
- `lookup_names_and_nicknames.md`
- `lookup_pet_names.md`
- `lookup_compliment_categories.md`

Source clusters routed here:
- `dark_academia_names`
- `cute_nickname_name_lists`
- `pet_names`
- `100_compliments`

## Phase 2: Clean Schema Expansion
Once the content stabilizes, split the most overloaded buckets into dedicated CharacterGen modules.

### Proposed new runtime buckets
- `dialogue_tone_patterns`
- `physicality_and_nonverbal_intimacy`
- `hurt_comfort_and_protection`
- `route_taxonomies`
- `scenario_engines`

### Proposed new prompt tags
- `{{dialogue_tone_patterns_reference}}`
- `{{physicality_intimacy_reference}}`
- `{{hurt_comfort_protection_reference}}`
- `{{route_taxonomies_reference}}`
- `{{scenario_engines_reference}}`

### Why these are the right splits
- `dialogue_tone_patterns` keeps line-shape steering away from theory and trope logic
- `physicality_and_nonverbal_intimacy` keeps touch, body language, and tenderness from being scattered
- `hurt_comfort_and_protection` is large enough to deserve its own runtime steering layer
- `route_taxonomies` keeps trope architecture separate from scene/event scaffolds
- `scenario_engines` gives first-message and scenario generation cleaner scene pressure inputs

## Phase 2 Code Changes
When promoting to new runtime bundles, update:
- `character_app/config.py`
  Add new bundle directories in `AppPaths`.
- `character_app/constants.py`
  Add new passthrough tags.
- `character_app/ui.py`
  Load the new bundles into generation context.
- `character_app/prompt_testing.py`
  Load and validate the new bundle tags.
- `scripts/bootstrap_local.py`
  Seed new bundle directories and expected files.
- `README.md`
  Document the new prompt tags and reference folders.

## Output Routing by Generation Surface

### Personality / Description
Primary inputs:
- `character_psychology_reference`
- `character_romance_craft_reference`

Future phase-two additions:
- `route_taxonomies_reference`

### Scenario
Primary inputs:
- `character_romance_craft_reference`
- `setting_scaffolds_reference`
- `romance_reference`

Future phase-two additions:
- `scenario_engines_reference`

### First Message
Primary inputs:
- `character_romance_craft_reference`
- `setting_scaffolds_reference`
- `narrative_pov_reference`

Future phase-two additions:
- `dialogue_tone_patterns_reference`
- `scenario_engines_reference`

### Speech Examples
Primary inputs:
- `character_psychology_reference`
- `explicit_dialogue_reference`
- `prompt_validation_reference`

Future phase-two additions:
- `dialogue_tone_patterns_reference`
- `hurt_comfort_protection_reference`
- `physicality_intimacy_reference`

## `novelist-ai` Role in This Plan
Use `novelist-ai` for:
- source triage
- source deduplication
- draft distillation
- weak-line cleanup
- output sanity-checks against romance craft expectations

Do not use `novelist-ai` for:
- deciding CharacterGen bucket boundaries
- naming CharacterGen runtime modules
- defining what gets loaded into prompts

## Grounded BDSM Source Routing
The following grounded BDSM source batch should be treated as a high-value distillation set because it fills gaps around:
- care
- trust
- reassurance
- attunement
- role motivation
- community and stigma
- sensory safety

### 1. Personal / Interpersonal / Sociocultural BDSM paper
Primary source:
- `Oh, Are You Just Kinky in Bed? Tying Together the Personal, Interpersonal, and Sociocultural Dimensions of BDSM`

Route to:
- `data/references/character_psychology`
  For stigma, shame, identity integration, safety, and emotional regulation.
- `data/references/character_romance_craft`
  For attunement, intimacy, negotiation, and relationship functioning.
- `data/references/prompt_validation`
  For anti-flattening rules that keep BDSM from being reduced to bedroom aesthetics.

Best future output files:
- `character_psychology/bdsm_identity_stigma_and_emotional_regulation.md`
- `character_romance_craft/care_trust_and_attunement_in_power_exchange.md`
- `prompt_validation/bdsm_source_quality_and_anti-flattening_rules.md`

### 2. Dominant motivation thesis
Primary source:
- `To know thyself`: motivating factors for dominants

Route to:
- `data/references/intimacy_archetypes`
  For grounded dominant motivation beyond cartoon control.
- `data/references/character_psychology`
  For role identity, self-concept, and meaning.

Best future output files:
- `intimacy_archetypes/dominant_motivations_and_stewardship.md`
- `character_psychology/power_exchange_identity_and_role_meaning.md`

### 3. Autistic adults kink paper
Primary source:
- `Comforting, Reassuring, and...Hot`

Route to:
- `data/references/character_romance_craft`
  For safety, reassurance, co-regulation, and sensory-aware intimacy.
- `data/references/explicit_dialogue`
  For grounded reassurance and negotiation language.
- future `hurt_comfort_and_protection`
  If phase-two schema expansion happens.

Best future output files:
- `character_romance_craft/sensory_safety_reassurance_and_erotic_trust.md`
- `explicit_dialogue/reassurance_negotiation_and_aftercare_language.md`

### 4. Turley thesis
Primary source:
- qualitative / phenomenological BDSM trust-care partnership material

Route to:
- `data/references/character_romance_craft`
  For care, trust, responsibility, and partner-mindedness.
- `data/references/intimacy_archetypes`
  For grounded role stewardship and surrender logic.

Best future output files:
- `character_romance_craft/care_trust_and_attunement_in_power_exchange.md`
- `intimacy_archetypes/submission_stewardship_and_surrender_logic.md`

### 5. Perks, problems, and the people who play
Primary source:
- qualitative dominant/submissive role study

Route to:
- `data/references/intimacy_archetypes`
  For empathy, nurturance, responsibility, attentiveness.
- `data/references/character_psychology`
  For role-linked stressors, benefits, and misconceptions.

Best future output files:
- `intimacy_archetypes/dominant_motivations_and_stewardship.md`
- `character_psychology/bdsm_role_benefits_risks_and_misreadings.md`

### 6. BDSM, becoming and the flows of desire
Primary source:
- identity-development / desire / belonging paper

Route to:
- `data/references/character_romance_craft`
  For discovery, belonging, first-attraction meaning, and identity formation.
- `design_reference` as selective support
  For conceptual backup rather than core runtime steering.

Best future output files:
- `character_romance_craft/desire_discovery_and_belonging_in_bdsm.md`

### Pending / needs cleaner review
These may be valuable, but should stay pending until read directly:
- PsycNet `2015-14979-005`
- PsycNet `2027-52442-001`
- PMC `10902275`
- PMC `9825129`
- the ProQuest dissertation

Do not route these into active file plans until they are inspected directly.

## Build Order
Recommended implementation order:
1. `character_psychology`
2. `character_romance_craft`
3. `explicit_dialogue`
4. `setting_scaffolds`
5. `romance_tropes`
6. `prompt_validation`
7. optional phase-two schema split

## Immediate Next Files to Author
If we start from the current cluster map, the highest-value first files are:
- `data/references/character_psychology/attachment_under_stress_and_affection_avoidance.md`
- `data/references/character_romance_craft/everyday_love_and_nonsexual_intimacy.md`
- `data/references/explicit_dialogue/confession_dialogue_patterns.md`
- `data/references/explicit_dialogue/hurt_comfort_and_protective_dialogue.md`
- `data/references/setting_scaffolds/meet_cute_meet_ugly_and_chaotic_intro_engines.md`
- `data/references/romance_tropes/structured_relationship_formats.md`
- `data/references/prompt_validation/romance_reference_deduplication_rules.md`

That order gives CharacterGen the fastest gain in:
- character believability
- route logic
- speech differentiation
- scenario usefulness
- ingest hygiene

### BDSM-focused next file set
From the grounded BDSM source batch, the highest-value follow-up files are:
- `data/references/character_romance_craft/care_trust_and_attunement_in_power_exchange.md`
- `data/references/intimacy_archetypes/dominant_motivations_and_stewardship.md`
- `data/references/character_romance_craft/sensory_safety_reassurance_and_erotic_trust.md`
- `data/references/explicit_dialogue/reassurance_negotiation_and_aftercare_language.md`
- `data/references/prompt_validation/bdsm_source_quality_and_anti-flattening_rules.md`

That sequence closes the biggest remaining gaps in:
- power-dynamic relationship realism
- non-cartoon dominant/submissive logic
- safety and reassurance language
- grounded erotic trust
- source hygiene for BDSM material
