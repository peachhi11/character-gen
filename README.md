# CharacterGen
## Overview
An AI-powered character card, persona matching, local chat, and world lorebook toolkit with intelligent context handling and cascading regeneration capabilities.

CharacterGen is evolving into a one-stop local workspace for building roleplay-ready character ecosystems: v2 and v3 character cards, matched user personas, prompt/reference libraries, local character-card chat, and world lorebook scaffolding. The current app is Python-based and still keeps the original card-generation workflow at its core, using base prompts, user input, reference context, and customizable field order to generate structured character and persona assets.

## Attribution
This project began from the skeleton of CygnusXGithub's original CharacterGen project, then diverged substantially into a heavily modified local character-generation toolkit: https://github.com/CygnusXGithub/CharacterGen

## Current Functional Features

- **Character Card Generation**:
  - Create and edit v2 and v3 character cards
  - Use the UI as a first-class CCv3 character card editor wrapper
  - Convert legacy v1/v2 cards into v3 card structures
  - Generate core card fields from configurable prompts
  - Regenerate one field at a time
  - Cascade regeneration through dependent fields
  - Load and save character cards as JSON or PNG with embedded card metadata
- **Persona Match Workflow**:
  - Dedicated `Persona Match` workflow for building a user persona around a reference character
  - Load reference characters from saved cards or external JSON/PNG files
  - Use a separate persona prompt library and output folder
  - Generate persona assets from reference-character context
- **Prompt And Reference System**:
  - Save and load different base prompt sets
  - Use conditional prompt sections based on user input
  - Use field references such as `{{name}}`, `{{description}}`, and `{{personality}}`
  - Use built-in reference bundles for romance, psychology, dialogue, setting, and related generation guidance
  - Control generation order so fields can build on earlier generated context
- **Local Runtime Support**:
  - One local launch path through `./start.sh`
  - One local bootstrap path through `./bootstrap.sh`
  - Shared external virtual environment at `~/.charactergen-venv`
  - Local `.env` support for API keys and endpoint overrides
- **Validation And Utility Modules**:
  - Character-card schema validation utilities
  - PNG metadata parsing and card conversion utilities
  - Trope-engine catalog and preset validation modules
  - Local tests for many backend parsing, validation, prompt, and runtime-state helpers

## In Progress / Not Fully Functional Yet

- **Local Character Card Chat App**:
  - Backend/runtime pieces exist for chat state and runtime chat handling
  - A polished end-to-end local chat UI is not functional yet
  - Group chat UI is planned but not complete
- **World Lorebook Builder**:
  - Reference material and lorebook export notes exist
  - A complete lorebook builder UI/export workflow is not functional yet
- **One-Stop App Integration**:
  - The goal is one cohesive app for character cards, personas, chat, lorebooks, references, and trope workflows
  - These pieces currently exist in separate modules/workflows and still need integration cleanup
- **Configuration UI**:
  - Runtime config works through files and environment variables
  - A dedicated in-app configuration tab is not complete yet
- **Advanced Card Metadata Editing**:
  - Core generated fields are editable
  - Full editing for every advanced v2/v3 metadata field such as creator, version, tags, and creator notes still needs cleanup
- **Quality-of-Life UI Features**:
  - Token counting, tag cheat sheets, richer hover help, and broader AICharED-style card editor conveniences are still planned

## Generation Tab
![GenTab](/images/GenTab.png)
  
## Base Prompt Tab
![BasePrompts](/images/basePrompt.png)
## Roadmap
The immediate roadmap is to turn the existing separate workflows into one cohesive local app: character card creation, persona matching, prompt/reference management, local character chat, group chat, and lorebook/worldbuilding support.

## Local Bootstrap

### Prerequisites
- Python 3.14 or 3.11

### First-time setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/CharacterGen.git
   cd CharacterGen
   ```
2. Run the local bootstrap:
   ```bash
   ./bootstrap.sh
   ```

`bootstrap.sh` is idempotent. It:
- creates or reuses the CharacterGen runtime venv at `~/.charactergen-venv` by default
- installs the pinned Python dependencies from `requirements.txt`
- recreates the runtime venv automatically if `pip`, PyQt6, or other required imports are broken
- seeds any missing local files from `bootstrap_assets/`
- verifies the pinned PyQt6 runtime can start a `QApplication`
- verifies `data/config/config.yaml`, `data/config/template.json`, character prompt assets, and persona prompt assets
- runs a non-GUI smoke test against the core save/load and prompt services

### API configuration

If `data/config/config.yaml` does not exist, bootstrap creates it from `bootstrap_assets/config/config.example.yaml`.

Create a local `.env` file for secrets:

```bash
cp .env.example .env
```

For OpenRouter, `API_URL` and `API_MODEL` live in `data/config/config.yaml`, while the API key lives in `.env`:

```yaml
API_URL: "https://openrouter.ai/api/v1/chat/completions"
API_MODEL: "@preset/janitor"
```

```bash
OPENROUTER_API_KEY=your-real-key
```

`start.sh`, `main.py`, and the config loader all resolve the same runtime config from the project root. Environment variables override file values where supported:
- `OPENROUTER_API_KEY` or `CHARACTERGEN_API_KEY`
- `CHARACTERGEN_API_MODEL`
- `CHARACTERGEN_API_URL`

For local OpenAI-compatible backends such as Oobabooga or KoboldCPP, set `API_URL` to the correct `/v1/chat/completions` endpoint. `API_MODEL` is only enforced when the configured URL targets OpenRouter.

### Launch

After bootstrap passes, start the desktop app with:

```bash
./start.sh
```

`start.sh` reruns the lightweight verification before launching `main.py`, so it doubles as the reliable day-to-day launch path on this machine.

By default, `start.sh` keeps the runtime environment outside the repo at `~/.charactergen-venv`. This avoids the Qt Cocoa plugin failures we were hitting when the venv lived inside the repo under `Documents/GitHub/CharacterGen`. You can override the path with `CHARACTERGEN_VENV_DIR=/custom/path ./start.sh` if needed.

## Usage

### Base Prompts Tab

The Base Prompts tab is where you configure the generation templates for each character field. The default prompt set includes a dedicated `personality` field so the app can separate broad character description from conversational behavior and emotional texture.

#### Available Tags
- Basic Field Tags:
  - `{{input}}`: User input insertion
  - `{{name}}`: Character name
  - `{{description}}`: Character description
  - `{{scenario}}`: Scenario information
  - `{{first_mes}}`: First message
  - `{{mes_example}}`: Message examples
  - `{{personality}}`: Personality traits

- Ignored Tags(Passed over and not replaced:
  - `{{char}}`: Ignored since they are used within silly tavern to replace Character names
  - `{{user}}`: Ignored since they are used within silly tavern to replace User names
- Persona Match Reference Tags:
  - `{{reference}}`: Full pasted or loaded reference-character context block
  - `{{reference_notes}}`: Alias for the full reference context block
  - `{{char_card}}`: Alias for the full reference context block
  - `{{char_name}}`, `{{char_description}}`, `{{char_personality}}`, `{{char_scenario}}`, `{{char_first_mes}}`, `{{char_mes_example}}`: Field-level values from the loaded reference character
- Built-in Reference Bundles:
  - `{{intimacy_reference}}`: BDSM archetype and compatibility reference material
  - `{{kink_reference}}`: Filtered grounded kink taxonomy for standard persona generation
  - `{{romance_reference}}`: Filtered romance trope and route-engine reference
  - `{{seduction_reference}}`: Distilled Robert Greene seduction-archetype reference
  - `{{explicit_dialogue_reference}}`: Filtered intimate-dialogue guidance for grounded, consenting adult speech examples
  - `{{narrative_pov_reference}}`: Character-side POV lock, scene-flow, and response-boundary guidance for grounded opening narration and runtime guardrails
  - `{{character_psychology_reference}}`: Grounded behavior, attachment, defense, and typed self-report psychology notes
  - `{{character_romance_craft_reference}}`: Wound/need/contradiction and scene/prose craft guidance for romance-focused generation, including CharacterGen-first reference governance
  - `{{setting_scaffolds_reference}}`: Grounded contemporary setting and micro-scene scaffold reference
  - `{{prompt_validation_reference}}`: Internal emotional-range and runtime validation guidance distilled from roleplay-bench and DeepDialogue
  - `{{lorebook_export_reference}}`: Future-facing lorebook structure and export rules for custom prompt work
  - `{{specialized_nsfw_reference}}`: Optional adult-only act taxonomy and normalized NSFW tag guidance
  - `{{worldbuilding_dynamic_lore_reference}}`: Future-facing dynamic-lore and reactive-world architecture guidance

### Additional Internal Design References
- `data/references/narrative_pov`: character-side POV lock, sensory-boundary, and active-scene guidance distilled from the recent runtime contract
- `data/references/character_psychology`: grounded psychology notes plus a cleaned typed self-report relationship corpus distilled from recent character-craft and forum-text sources
- `data/references/character_romance_craft`: wound/lie/want/need, name-seeding, romance-arc craft notes, CharacterGen-first ingest governance, and mined scene/prose guidance from helper writing stacks
- `data/references/setting_scaffolds`: grounded contemporary setting and micro-scene scaffolds distilled from recent location and romance scenario source files
- `data/references/lorebook_export`: future lorebook export, keyword, recursion, and validation rules
- `data/references/prompt_validation`: internal prompt and runtime validation criteria distilled from roleplay-bench work plus DeepDialogue emotion/domain testing notes
- `data/references/specialized_nsfw`: optional adult-only act taxonomies and tag-normalization notes for specialized mode work, kept separate from the standard grounded references
- `data/references/worldbuilding_dynamic_lore`: future dynamic-lore, reactive-world, and world-state scripting architecture notes
- `design_reference/charactergen_reference_module_plan.md`: CharacterGen-native mapping plan for routing clustered source material into runtime bundles without letting helper stacks define the schema
- `design_reference/grounded_bdsm_source_routing.md`: source-routing note for grounded BDSM research and qualitative material, mapped to CharacterGen bundle targets and planned outputs
  
- Conditional Input Tags:
  ```
  {{if_input}}
  Content only included when user provides input
  {{/if_input}}
  ```

#### Generation Order
- Set the order by numbering fields (1-6)
- Only reference tags from fields that come earlier in the generation order
- Fields without an order number are skipped during generation

### Generation Tab

#### Character Management
- Load/save characters using the top controls
- Character files are stored in the `data/characters` folder
- Save completed characters using the "Save Character" button
- To save as PNG make sure to load a picture first, otherwise a default is used

#### Field Generation
- **Name Field**: Toggle between direct input and generated name
- **Other Fields**: Input is optional, used as context in generation
- **Generation Controls**:
  - "Generate All": Sequential generation of all fields
  - 🔄: Regenerate single field
  - 🔄+: Cascading regeneration (updates dependent fields)

### Persona Match Tab

#### Reference Character Input
- Load a saved character from `data/characters`
- Open an external `.json` or `.png` character card as the reference source
- Paste or edit additional reference context directly in the reference text box

#### Persona Outputs
- Persona prompt sets are stored in `data/persona_prompts`
- Generated persona profiles are stored in `data/personas`
- The persona workflow uses the same field layout as character generation, but the prompts are intended to build a matching `{{user}}` persona around the loaded `{{char}}` reference

## Prompt Testing

CharacterGen now includes a local prompt-test harness so prompt changes can be checked against fixed cases before you trust a single sample output.

### Included Pieces
- Offline render harness: [scripts/test_prompts.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/scripts/test_prompts.py)
- Reusable test helpers: [character_app/prompt_testing.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/character_app/prompt_testing.py)
- Default prompt cases: [tests/prompt_cases](/Users/meganmckinnon/Documents/GitHub/CharacterGen/tests/prompt_cases)
- Reference-card fixtures: [tests/fixtures](/Users/meganmckinnon/Documents/GitHub/CharacterGen/tests/fixtures)
- Fast unit coverage: [tests/test_prompt_harness.py](/Users/meganmckinnon/Documents/GitHub/CharacterGen/tests/test_prompt_harness.py)

The prompt cases now include a small adversarial layer derived from roleplay-benchmark seeds, aimed at catching:
- agency drift
- POV/instruction drift
- continuity and lore contradiction failures
- narrative stagnation when the user goes passive

### Offline Checks

Runs prompt loading, reference-bundle injection, render checks, unresolved-tag checks, and prompt-case validation without calling the model:

```bash
python3 scripts/test_prompts.py
python3 -m unittest tests/test_prompt_harness.py
```

### Live Checks

Runs the configured API model against the fixed test cases and validates structural output expectations:

```bash
python3 scripts/test_prompts.py --live
```

Optional filters and report output:

```bash
python3 scripts/test_prompts.py --case persona_soft_match
python3 scripts/test_prompts.py --live --report logs/prompt-test-report.json
```

### Current Default Cases
- `character_workplace_rivals`: tests a contemporary high-status workplace-rivals male lead
- `persona_soft_match`: tests a softer unintentionally magnetic persona matched to a controlled dominant lead

## Tips
- Save different base prompt sets for different character types
- Use conditional tags to handle optional input gracefully
- Set generation order to build context progressively
- Use cascading regeneration to maintain consistency
