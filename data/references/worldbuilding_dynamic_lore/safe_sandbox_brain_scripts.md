# Safe Sandbox Brain Scripts for World Building and Dynamic Lore

## Purpose
This reference distills the useful systems ideas from the scripting guide in `dccueu (1).pdf` into a CharacterGen-ready design note for future world-building and dynamic-lore features.

It is not a prompt-writing source. It is a systems reference for future:
- world state
- NPC state
- relationship state
- emotional state
- fake memory state
- event-driven scene progression

## Non-Verbatim Rule
This file is implementation guidance, not output copy.

Use it to shape:
- systems design
- script safety
- event flow
- state handling

Do not let its scripting language or systems phrasing bleed directly into generated content.

The intended design style is:
- safe ES5-style JavaScript
- no-state-first design
- short append outputs
- event-driven behavior
- modular lore layers instead of giant monolith scripts

## Core Sandbox Rules Worth Keeping
- Treat `personality` and `scenario` as the only writable whiteboards.
- Read everything else from context; do not assume persistent mutable state.
- Prefer older safe syntax and simple control flow over modern JavaScript features.
- Keep every mutation short, local, and legible.
- Build behavior from many small reactions rather than one giant engine.

## Design Philosophy

### 1. No-State-First
Start by assuming you do not have true persistent memory.

Instead:
- infer from the current message
- infer from message count
- infer from time or environment
- append lightweight reminders into writable fields

This creates believable continuity without fragile state machines.

### 2. Short-Append
Every script mutation should be short enough to guide tone without bloating context.

Good:
- `", more relaxed now."`
- `" The room feels quieter than before."`
- `" They remember the user's preference for coffee."`

Bad:
- multi-paragraph rewrites
- repeated full summaries of prior events
- giant lore dumps every turn

### 3. Event-Driven
Scripts should react to:
- keyword/topic matches
- emotional cues
- progression milestones
- time of day
- setting mentions
- combinations of the above

Think:
- if this happens, nudge the state
- if this has happened long enough, unlock a deeper layer
- if multiple signals overlap, shift tone or scene texture

## The Five Dynamic State Families

### Emotional Dynamic State
Track tone through lightweight scoring or layered conditions.

Useful signals:
- praise
- insult
- fear
- jealousy
- comfort
- confession
- flirtation

Good pattern:
- accumulate small score changes
- translate the score into a brief emotional modifier
- let the same setting feel different under different moods

### Relationship State
Use message-count ranges and repeated topics to simulate:
- caution
- growing familiarity
- trust
- intimacy
- possessiveness
- strain
- rupture
- repair

Best use:
- early chat: formal or guarded
- mid chat: warmer, more open
- later chat: stronger bond, deeper reveals, heavier consequences

### Memory State
Use fake memory sparingly and only for high-value facts.

Good candidates:
- names
- likes/dislikes
- recurring fears
- promises
- unresolved conflict
- recent injuries or stressors

Store as:
- compact reminders in `scenario`
- small relational cues in `personality`

Avoid:
- logging every detail
- endless accumulation without pruning

### Dynamic World State
Make the world move independently of dialogue.

Useful tools:
- timed event beats
- low-probability ambient events
- weather or atmosphere shifts
- location-based scene variants
- day/night changes

Purpose:
- make scenes feel alive
- create pacing beats
- reinforce tone without hijacking the interaction

### Dynamic NPC State
NPCs should not be static labels.

Track them through:
- category-based lore entries
- relationship role to the main pair
- scene pressure function
- occasional event-driven reactivation

NPC functions:
- witness
- rival
- caretaker
- temptation
- social pressure
- logistical blocker
- messenger

The goal is not full simulation. The goal is selective activation when the story needs pressure.

## System Patterns Worth Reusing

### Progressive Reactions and Pacing
Message count can simulate stages of a relationship or route.

Use ranges, not just exact counts:
- 1-5 cautious
- 6-15 warming
- 16-30 familiar
- 31+ emotionally established

This works well for:
- relationship escalation
- comfort levels
- reveal timing
- route-specific milestones

### Fake Memory and Context Recall
The guide's strongest practical lesson is that fake memory works best when:
- it is brief
- it is selective
- it reinforces consistency
- it is not treated like a full database

For CharacterGen, that means future dynamic lore should preserve only:
- high-signal personal facts
- current emotional carryover
- one or two unresolved tensions

### Dynamic Triggers and Combined Conditions
Single-keyword triggers are weak.
Combined triggers are stronger:
- topic + emotion
- topic + time
- topic + progression stage
- setting + mood

This is how scenes start to feel authored instead of mechanical.

### Event Lore
Randomized ambient events are useful when they are:
- rare
- brief
- mood-supportive
- non-disruptive

Use for:
- bells
- weather shifts
- footsteps
- distant noises
- lights flickering
- doors opening
- texts arriving

Do not use for:
- major plot turns every few messages
- giant atmospheric paragraphs
- events that erase the user's focus

### Weighted Lore and Probability
Not everything should trigger every time.

Use weighted outcomes for:
- common vs rare reactions
- emotional variance
- memory resurfacing
- scene texture
- NPC interruptions

Important rule:
- core canon should be stable
- texture can vary

### Min/Max Message Gating
Gates are useful for unlockable content:
- secrets
- intimacy layers
- trust shifts
- route-specific reveals
- recurring world details

Use them to avoid:
- instant overexposure
- repetitive early oversharing
- late-stage emotional depth arriving too early

### Time and Environment Awareness
Same location, different hour, different feeling.

Good dynamic layers:
- daylight vs night
- public vs private
- weekday vs weekend
- storm vs quiet
- crowded vs empty

This is especially strong for future world-building tabs because it creates reusable scene variants without rewriting the world from scratch.

### Lorebooks and Hierarchies
As systems grow, entries should be grouped by theme:
- places
- moods
- people
- weather
- memories
- conflicts
- events

Hierarchy matters because it prevents chaos.

Recommended rule:
- choose priority order explicitly
- let stronger current-state layers override weaker ambient ones

Example priority:
1. safety or crisis state
2. relationship state
3. emotional state
4. location state
5. ambient event texture

### Shifts and Conditional Layers
The same base setting should render differently depending on state.

Examples:
- forest at night vs forest at noon
- same apartment during rupture vs comfort
- same college hallway under jealousy vs under flirtation

This is the core of dynamic lore:
- base world
- layered modifiers
- state-aware output

### Reaction Engines and Scoring Systems
Scoring is useful for emotional intensity, not just binary triggers.

A future engine can map signals into:
- irritation
- trust
- desire
- shame
- curiosity
- protectiveness

Then translate score bands into short state notes.

This is more robust than writing isolated one-off triggers forever.

### Adaptive Engines and Hybrid States
Best dynamic behavior comes from mixing:
- trigger matches
- emotional scoring
- world state
- relationship progression
- weighted variance

That mix creates:
- adaptive scene texture
- more believable continuity
- less rigid feeling behavior

### Everything Lorebook Framework
The most useful high-level takeaway is not "one giant script."
It is:
- one unified framework
- multiple modular categories
- clear priority order
- reusable entries

For CharacterGen, the future world-building system should aim for:
- structured modules
- not one giant prompt blob
- not one giant script blob

## Recommended CharacterGen Future Architecture

### 1. Base World Layer
Stores stable facts:
- city
- school
- workplace
- household
- organizations
- recurring NPCs

### 2. Relationship Layer
Stores evolving relational state:
- trust
- tension
- intimacy
- conflict
- disclosure stage

### 3. Emotional Engine Layer
Stores current emotional shading:
- calm
- irritated
- flustered
- jealous
- comforted
- guarded

### 4. Event Layer
Stores ambient or milestone events:
- weather
- interruptions
- message-count beats
- route triggers

### 5. Memory Layer
Stores compact carryover:
- names
- preferences
- current unresolved issues
- recent promises or wounds

## Implementation Guidance

### Use Safe ES5-Style
Prefer:
- `var`
- classic `for` loops
- `indexOf`
- `Math.random`
- simple regex

Avoid:
- arrow functions
- async logic
- complex array methods in fragile environments

### Keep Outputs Small
Every write should be:
- one phrase
- one clause
- one sentence

World building should feel cumulative, not spammy.

### Prefer Layered Data Over Giant Logic
Use data structures for entries and small loops over them.

That makes future systems:
- editable
- debuggable
- modular
- easier to tune per route

### Break Early
If a match is found in a loop, stop scanning.

### Separate Core from Texture
Core:
- stable facts
- high-priority route logic

Texture:
- ambient events
- weighted mood flourishes
- minor environmental variation

### Test by Message Stage
Future dynamic-lore tests should check:
- first five messages
- mid-stage familiarity
- late-stage emotional depth
- scene after conflict
- scene after intimacy

## Best Practices to Carry Forward
- keep systems modular
- keep writes short
- prefer state cues over full rewrites
- use ranges more than one-off exact numbers
- treat randomness as seasoning
- prioritize continuity over spectacle
- build world reactions that support the scene instead of replacing it

## What Not to Import Literally
- giant append-heavy personality growth on every single turn
- uncontrolled fake memory accumulation
- random events firing too often
- giant nested conditional chains
- single giant all-purpose script without categories

## CharacterGen Takeaway
The PDF is most valuable as a future architecture note for a World Building or Dynamic Lore tab.

The right lesson is not:
- "copy these scripts directly"

The right lesson is:
- use safe, modular, event-driven layers to simulate emotional state, relationship state, memory state, world state, and NPC pressure without requiring full persistent memory or unsafe complexity.
