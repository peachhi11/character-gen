# Character Card Intro Engine Architecture

## Purpose
This note is the high-level architecture map for the introduction engines currently feeding CharacterGen's route and scene references.

It is for:
- app logic
- reference planning
- route-state design
- future variable-driven card compilation

It is not a user-facing prose module.

## Non-Verbatim Rule
Do not echo this architecture back out as card prose or scenario copy.

Use it to:
- choose engine families
- route state variables
- map likely arc outcomes
- decide which runtime references should be loaded more heavily

## Core Flow
`Input Engine Type -> Process Branch Logic -> Compile Arc Route`

Useful app-side expansion:
`App UI: User Tweak Inputs -> Back-end: Trope Logic Compiler -> JSON Card Gen / Dynamic Prompt / UI State Map`

The four current introduction architectures are:
- `Meet-Cute`
- `Meet-Ugly`
- `Meet-Crazy`
- `Forced-Proximity`

Each engine should answer:
- what the baseline emotional weights are
- what branch logic changes the route state
- what arc outputs the pairing can credibly support

## Character Card Data Schema
To make the engine usable in a card-creation app, each card should be split into three operational layers:

### 1. Static Metadata
This should hold:
- name
- visual attributes
- archetype label
- base relationship framing
- current route phase

### 2. Trope Weights
These are the engine inputs.

They should hold the current numeric state for:
- tension
- trust
- desire
- fear
- denial
- route-specific pressure values

### 3. Contextual Dialogue Triggers
These should hold:
- phase-specific dialogue nodes
- trigger conditions
- action prompts
- state-dependent alternate outputs

Useful generation rule:
- static metadata describes the card
- trope weights drive behavior
- dialogue triggers expose the behavior in play

## Standardized JSON Output Structure
The exported card payload should be clean, stateful, and platform-agnostic.

Useful top-level sections:
- `card_id`
- `metadata`
- `trope_engine_weights`
- `origin_context`
- `dialogue_nodes`

### Reference example
```json
{
  "card_id": "char_00921_rival",
  "metadata": {
    "name": "Julian Vance",
    "archetype": "The Academic Ice-Wall",
    "engine_type": "Meet-Ugly",
    "current_phase": 1
  },
  "trope_engine_weights": {
    "rivalry_heat": 4,
    "romantic_tension": 0,
    "repressed_desire": 2,
    "fear_of_loss": 3,
    "lie_active": false,
    "lie_count": 0,
    "angst_meter": 1
  },
  "origin_context": {
    "environment_type": "Academic",
    "incident_summary": "Stole the final critical thesis textbook copy.",
    "spark_token": "The shared research notes with coffee stains.",
    "unbreakable_tether": "Assigned as co-authors on the career-making publication."
  },
  "dialogue_nodes": {
    "phase_1_baseline": {
      "greeting": "Oh, look. The resident expert arrived. Try not to break anything today.",
      "body_language_descriptor": "They do not look up from their laptop, but their typing speed accelerates sharply."
    },
    "phase_4_breaking_point": {
      "activation_condition": "romantic_tension >= 4",
      "dialogue_payload": "I don't hate you. I fight with you because it's the only time you look at me with absolute focus.",
      "action_prompt": "They step directly into your space, knuckles white against the desk."
    },
    "phase_5_hangover_crisis": {
      "if_player_lied": "A tactical error driven by cortisol levels. Let's forget it.",
      "if_player_honest": "Even now? When there's nothing left to hide behind?"
    }
  }
}
```

Useful generation rule:
- each engine should be able to mint its own data into the shared `origin_context`
- legacy engine-specific origin blocks can still be normalized in the validator
- the shared schema should stay consistent even when the route family changes

## Format Strategy
The repo supports two different storage tracks on purpose.

### Standard Character Cards
These remain compatible with the existing `chara_card_v2` editor flow.

Supported formats:
- `.json`
- `.png` with embedded `chara` metadata

### Engine-State Trope Cards
These are the structured route-state cards described by the trope engine schema.

Supported format:
- `.json` only

Explicit rule:
- engine-state cards must not be embedded into PNG metadata
- PNG metadata embedding is reserved for standard character cards until there is a dedicated engine-state image format strategy

## Runtime State Separation
Immutable card assets and volatile runtime session state should not share the same save path.

Architecture rule:
- V2 and V3 character cards remain immutable source assets
- active trope-engine session analytics live in a separate `EngineStateCard` runtime object
- session saves are written under a dedicated runtime-saves directory, not back into the base card asset files

Useful split:
- base card asset = stable authoring template
- engine-state session = current phase, live weights, chat backlog, and save-game continuity

## Compatibility Layer
The repo now supports a compatibility layer around the canonical engine-state schema.

Supported compatibility paths:
- `Character Card V2` payloads with `data.extensions.trope_engine`
- `Character Card V3` payloads with `extensions.trope_engine`
- legacy flat `V1` cards upgraded into `V3` with trope-engine defaults

Useful implementation split:
- canonical trope-engine cards remain the source-of-truth authoring schema
- V2 and V3 payloads act as wrapper formats for standard card ecosystems
- PNG metadata utilities only accept wrapped V2 or V3 character-card payloads

## Structural Schema Validation Rules
Every uploaded or generated engine-state card should pass a four-tier structural check before it is saved, surfaced in the UI, or injected into chat runtime.

Validation flow:
`Incoming JSON -> Metadata Check -> Core Weight Bounds -> Dialogue Nodes -> Logical Sanity`

### Tier 1. Metadata Check
Required rules:
- `card_id` must be a non-empty string
- `metadata.engine_type` must resolve to one supported engine family
- `metadata.current_phase` must be an integer between `1` and `6`

Compatibility rule:
- older payloads may still expose `metadata.base_relationship`
- the validator may backfill `metadata.engine_type` from that legacy field, but it should warn when it does so

### Tier 2. Core Weight Bounds
Required rules:
- `trope_engine_weights` must be an object
- required route weights must exist for the selected engine
- weight values may only be integers or booleans
- no weight may be `null`
- integer weights are normalized into the `0..5` range

Engine-specific required weight examples:
- `Meet-Cute`: `platonic_trust`, `romantic_awareness`
- `Meet-Ugly`: `rivalry_heat`, `repressed_desire`
- `Meet-Crazy`: `chaotic_chemistry`, `adrenaline_level`
- `Forced-Proximity`: `confinement_stress`, `proximity_heat`

### Tier 3. Contextual Dialogue Completeness
Required rules:
- the engine-specific origin block must exist
- origin token fields must be non-empty strings
- `dialogue_nodes` must be present as an object
- transition nodes should declare a `trigger_condition` as a script string or boolean

Fallback rule:
- if a transition node omits a trigger condition, the validator may inject a safe fallback condition instead of letting the UI fail open

### Tier 4. Logical Sanity and Mutex Checks
Required rules:
- `lie_active == true` cannot coexist with `lie_count == 0`
- `lie_active == true` cannot initialize with `rivalry_heat == 0`
- `angst_meter == 5` and `platonic_trust == 5` should be rejected as a soft-lock risk

Useful practical rule:
- structural validation should reject contradictions that would force the chat layer into incoherent emotional states before the first turn even starts

## Validation Matrix
Useful backend responses:

| Data Node | Invalid State | Expected Validator Response |
| --- | --- | --- |
| `engine_type` | Outside the core supported engines | Fail validation |
| Numeric weight | `< 0` or `> 5` | Clamp to `0` or `5` and warn |
| `lie_active` | `true` while `rivalry_heat == 0` | Fail validation |
| Dialogue transition node | Missing condition | Inject fallback trigger and warn |
| Origin token field | Missing or blank string | Fail validation |

## Runtime Validator
The repo-side validator for this schema lives here:
- [trope_engine_character_card.schema.json](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/schemas/trope_engine_character_card.schema.json:1)
- [character_card_v2_with_trope_engine.schema.json](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/schemas/character_card_v2_with_trope_engine.schema.json:1)
- [character_card_v3_with_trope_engine.schema.json](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/schemas/character_card_v3_with_trope_engine.schema.json:1)
- [card_schema_validation.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/card_schema_validation.py:1)
- [card_format_conversion.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/card_format_conversion.py:1)
- [png_metadata_engine.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/png_metadata_engine.py:1)
- [legacy_v1_parser.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/legacy_v1_parser.py:1)
- [live_chat_state.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/live_chat_state.py:1)
- [runtime_state.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/runtime_state.py:1)
- [autosave_daemon.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/autosave_daemon.py:1)
- [fastapi_server.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/fastapi_server.py:1)
- [prompt_mapper.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/prompt_mapper.py:1)
- [cards.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/cards.py:1)
- [validate_character_card_schema.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/scripts/validate_character_card_schema.py:1)
- [test_card_schema_validation.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/tests/test_card_schema_validation.py:1)

Useful implementation rule:
- the design note owns the rules
- the JSON Schema file owns the canonical machine-readable contract
- the validator module owns executable enforcement
- the format conversion layer translates wrapped V2/V3 cards into canonical trope-engine state
- the PNG metadata engine handles standard character-card embedding and extraction
- the legacy parser upgrades flat V1 cards into trope-engine-extended V3 payloads
- the live chat analyzer mutates runtime state during play loops
- the runtime-state controller owns session saves, live metric edits, and chat backlog persistence
- the autosave daemon drains runtime saves asynchronously without blocking request/response flow
- the FastAPI server exposes chat-turn processing, editor overrides, and session retrieval endpoints
- the prompt mapper turns validated state into deterministic runtime system instructions
- the repository enforces validation on raw engine-state JSON import/export
- the CLI script gives the app and local tooling one stable validation entrypoint

## Front-End Interaction Logic Map
The app UI should make invisible route state legible without turning the card into a spreadsheet.

### High rivalry heat
Useful UI effects:
- tense or combative status ring
- sharper text tone
- more defensive or one-upmanship flavored surface behavior

### Spiking romantic tension
Useful UI effects:
- warmer avatar grading
- slower breathing animation
- more sensory and micro-fixated output keywords
- more loaded pauses and gaze logic

### `Lie_Active == true`
Useful UI effects:
- `Guarded` or equivalent state label
- affectionate options lock or gray out
- more formal, distant language variants surface instead

Useful generation rule:
- the UI should not merely display numbers
- it should tell the user what emotional mode the card is currently performing

## Code Architecture For App Implementation
The app core can treat the card builder as a constructor that applies engine templates and emits serializable state.

### Reference constructor shape
```python
class CharacterCardConstructor:
    def __init__(self, name, trope_style):
        self.name = name
        self.trope_style = trope_style
        self.rivalry_heat = 0
        self.romantic_tension = 0
        self.lie_active = False
        self.meet_context = {}

    def apply_meet_crazy_template(self, spectacle, lock, hangover_token):
        self.rivalry_heat = 1
        self.romantic_tension = 2
        self.meet_context = {
            "type": "Meet-Crazy",
            "spectacle": spectacle,
            "lock": lock,
            "token": hangover_token
        }
        return self.__dict__
```

Useful generation rule:
- the constructor should not hardcode prose outcomes
- it should initialize state that the prompt layer and UI layer can interpret

## Prompt Engineering Injection Model
If the card is being fed into an LLM chat backend, the app should pass structured state, not only a descriptive personality paragraph.

Useful system-emulation rules:
1. keep `meet_context` available as a core memory token
2. if `lie_active` is true, reject direct romantic advances with defensive or formal deflection
3. increment relevant tension variables when the user closes distance or forces a branch trigger
4. when a threshold is hit, stop generic chatting and force the correct dialogue tree

### Reference injection shape
```text
[SYSTEM EMULATION RULES]
You are tracking an interactive card object. Current data state: {minted_card_data}.
1. Maintain the 'meet_context' as a core memory token. Reference it subtly every 15 turns.
2. If 'lie_active' is true, reject any direct player romantic advances with a sharp, defensive deflection.
3. Every time the user choice steps into personal space, increment 'romantic_tension' by 1.
4. When 'romantic_tension' hits 4, stop normal chatting and force execution of the 'phase_4_breaking_point' dialogue tree.
```

Useful generation rule:
- prompt injection should expose stateful rules, not dump the whole design doc into the system prompt

## Engine Map

### 1. Meet-Cute
Default baseline:
- high safety
- low resistance
- early comfort
- easy platonic trust growth

Primary variables:
- `platonic_trust`
- `romantic_awareness`
- `fear_of_loss`

Typical outputs:
- slow burn confidant route
- sexy awkward route

Runtime references:
- `setting_scaffolds/meet_cute_meet_ugly_and_chaotic_intro_engines.md`
- `romance_tropes/friends_to_lovers_route_engines.md`

### 2. Meet-Ugly
Default baseline:
- high friction
- low admitted attraction
- strong rivalry or status opposition

Primary variables:
- `rivalry_heat`
- `romantic_tension`
- `repressed_desire`
- optional `lie_active`

Typical outputs:
- professional truce route
- explosive pressure-release route

Runtime references:
- `romance_tropes/enemies_to_lovers_route_engines.md`

### 3. Meet-Crazy
Default baseline:
- very high chaos
- high adrenaline
- low initial grounded intimacy

Primary variables:
- `chaotic_chemistry`
- `adrenaline_level`
- `emotional_depth`
- `angst_meter`

Typical outputs:
- golden chaos route
- hangover-crisis route

Runtime references:
- `setting_scaffolds/meet_cute_meet_ugly_and_chaotic_intro_engines.md`

### 4. Forced-Proximity
Default baseline:
- spatial pressure
- rising stress
- unavoidable body-awareness
- intimacy driven by confinement rather than spectacle

Primary variables:
- `confinement_stress`
- `proximity_heat`
- `safety_rating`
- `distance_locked`

Typical outputs:
- vulnerable thaw
- breaking-point pressure cooker

Runtime references:
- `romance_tropes/forced_proximity_route_engines.md`

## State Evaluator Layer
At climax, the engine should compile the ending from accumulated route state rather than from trope label alone.

Useful high-level checks include:
- whether lies were resolved
- whether angst stayed manageable
- whether chaos converted into depth
- whether distance locked permanently

### Reference evaluator shape
```python
def evaluate_climax_state(card_data):
    if card_data["lie_count"] == 0 and card_data["angst_meter"] <= 1:
        return "ROUTE_FLAWLESS_TRUTH"
    elif card_data["chaotic_chemistry"] >= 4 and not card_data["distance_locked"]:
        return "ROUTE_PARTNERS_IN_CRIME"
    elif card_data["emotional_depth"] >= 4 and card_data["angst_meter"] <= 3:
        return "ROUTE_GROUNDED_SANCTUARY"
    else:
        return "ROUTE_BITTER_SEPARATION"
```

Useful output families:
- `ROUTE_FLAWLESS_TRUTH`
- `ROUTE_PARTNERS_IN_CRIME`
- `ROUTE_GROUNDED_SANCTUARY`
- `ROUTE_BITTER_SEPARATION`

## Practical Rule
No single engine should try to carry every route.

Instead:
- intro engine sets the baseline
- branch logic modifies the chemistry
- later references decide the payoff style

The clean architecture split is:
- design note defines schema and compiler rules
- runtime route references define emotional logic by engine family
- UI maps those values into visible state
- chat prompting reads the current state object rather than reconstructing it from scratch

## CharacterGen Takeaway
The architecture is strongest when:
- engine type explains the first contact pressure
- variables explain why the pair reacts the way they do
- the final route state feels earned by accumulated choices

The target is not generic romance categorization.
The target is a reusable state machine for believable character-card chemistry.
