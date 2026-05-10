# CharacterGen
## Overview
An AI-powered character card generator and editor with intelligent context handling and cascading regeneration capabilities.

CharacterGen is a Python-based application for creating and editing v2 character cards. It uses a prompt system that combines base prompts with user input and contextual information to generate character attributes in a customizable order.

## Features

- **Character Management**:
  - Load and save character cards in JSON or PNG format
  - Edit generated outputs
  - Single field regeneration
  - Cascading regeneration for dependent fields
- **Ease Of Use**:
  - Field focus, a way to expand a field or multiple that you are working on to a much larger text area.
  - Ability to generate/save multiple first messages with one as the main first message and the rest going into alternate greetings.
  - Append generated message examples easily.
- **Base Prompt System**:
  - Save and load different prompt sets
  - Conditional content based on user input
  - Context-aware field references
- **Intelligent Context Generation**: Uses a tag-based system for precise context placement
- **Flexible Generation Order**: Customizable field generation sequence with dependency handling

## Generation Tab
![GenTab](/images/GenTab.png)
  
## Base Prompt Tab
![BasePrompts](/images/basePrompt.png)

   

## Planned Features
   (in progress)
  - Editing of the other fields making up a v2 card such as creator, version, tags etc.
  - adding more conditional tags such as {{if_no_input}}
  - Configuration tab to pass some simple generation perameters like max tokens, as well as be a place to include other configuration options.
  - Saving the user prompts into the card to be repopulated when loading a card, this could also be done with the basePrompts used for generating that card.
  - AICharED made by Zoltan, AVA, and Neptune has alot of nice features that I like but may never get around to adding them. I would enjoy implementing their better UI formatting, and maybe QoL features such as:
    - a tag cheat sheet with quick copy
    - info on hover for each fields function
    - token counter with breakdown

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
- creates or reuses `.venv`
- installs the pinned Python dependencies from `requirements.txt`
- recreates `.venv` automatically if `pip`, PyQt6, or other required imports are broken
- seeds any missing local files from `bootstrap_assets/`
- verifies the pinned PyQt6 runtime can start a `QApplication`
- verifies `data/config/config.yaml`, `data/config/template.json`, and prompt assets
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

## Usage

### Base Prompts Tab

The Base Prompts tab is where you configure the generation templates for each character field. Current default prompt does not include generating personality field.

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

## Tips
- Save different base prompt sets for different character types
- Use conditional tags to handle optional input gracefully
- Set generation order to build context progressively
- Use cascading regeneration to maintain consistency
