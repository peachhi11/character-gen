# Forced Proximity Route Engines

## Purpose
This reference covers route logic for romances driven by spatial confinement, enforced cohabitation, one-room traps, shared shelter, and other forms of inescapable closeness.

Use it when CharacterGen needs:
- stronger `Scenario` structure for forced-proximity romance routes
- better logic for intimacy created by spatial pressure rather than immediate trust or spectacle
- cleaner `First Message Examples` where the room itself functions as a romance engine
- branching guidance for interactive or game-like confinement-to-intimacy design

This is not a generic “only one bed” note.
It is a route-engine reference for proximity pressure.

## Non-Verbatim Rule
Do not reuse these variables, arc routes, or branch structures verbatim.

These patterns are inspiration only.
Generated output should always be unique and tailored to the individual pairing's:
- age
- relationship baseline
- stress tolerance
- privacy level
- physical confidence
- emotional guardedness

If the output starts sounding like stored trope scaffolding instead of the pair's actual spatial dynamic, rewrite it.

## Core Rule
Forced-proximity romance works when space becomes pressure.

The trap should:
- limit escape
- increase body-awareness
- make emotional withdrawal harder
- force repeated negotiation over distance, safety, and control

It should not be:
- random logistics with no tension
- instant intimacy with no discomfort
- confinement that never changes the pair's behavior

## Structural Architecture And Variable Weights

Useful baseline:

```json
{
  "engine_type": "Forced-Proximity",
  "starting_weights": {
    "confinement_stress": 1,
    "proximity_heat": 1,
    "safety_rating": 2,
    "distance_locked": false
  }
}
```

Useful generation rule:
- this engine starts lower and tighter than meet-crazy
- the pressure rises through duration, not spectacle

## Branch Logic Matrix

### The Claustrophobia Metric
When `confinement_stress >= 3`:
- environmental text should intensify
- breathing, temperature, noise, and micro-distance matter more
- irritation, silence, or panic can sharpen quickly

Useful generation rule:
- the environment should feel more physical as stress rises

### The Territorial Play Branch
When `proximity_heat >= 3`:
- mock-fights over space become charged
- small touches gain meaning
- boundary negotiation becomes flirtation
- territoriality can function as foreplay, challenge, or protection

Useful generation rule:
- heat should come from how the pair occupies space, not only from explicit confession

### The Steel Vault Branch
When `distance_locked == true`:
- one character is trying to emotionally withdraw despite physical closeness
- the room becomes angsty rather than merely intimate
- every tiny forced contact now feels overdetermined

Useful generation rule:
- this branch should spike internal pressure, not reduce it

## Route Variables

### `Confinement_Stress`
High values mean:
- sharper sensory awareness
- lower patience
- more visible strain
- more likely accidental emotional exposure

### `Proximity_Heat`
High values mean:
- stronger reaction to touch, breath, warmth, and distance breaches
- more flirtation hidden inside irritation or practical negotiation
- more likely physical breakthrough

### `Safety_Rating`
High values mean:
- the room or trap begins to feel protective instead of threatening
- shared stillness becomes possible
- emotional honesty lands more cleanly

### `Distance_Locked`
True means:
- one or both characters are refusing what the closeness is doing to them
- the route is in defensive mode
- future payoff becomes more explosive or more painful

## Arc Routes

### Route A: The Vulnerable Thaw
Progression:
- isolation trap snaps shut
- environmental stress rises
- `safety_rating` climbs
- the pair share psychological exposure
- gentle grounding replaces defensive posture

Resolution output:
- the physical cage becomes a sanctuary
- guarded characters finally stop performing armor

### Route B: The Breaking-Point Pressure Cooker
Progression:
- isolation trap snaps shut
- contrast in temperament or goals creates friction
- `confinement_stress` peaks
- spatial collision becomes unavoidable
- emotional or physical release finally detonates

Resolution output:
- the confinement forces a breakthrough that years of ordinary life would have delayed

## Common Forced-Proximity Setups

Useful traps include:
- one-room shelter
- blizzard or storm lock-in
- broken elevator
- safe house
- road trip rooming issue
- only one bed
- shared apartment crisis
- quarantine or magical seal
- stakeout with no privacy

Useful generation rule:
- the trap should shape the romance mechanics, not just the furniture layout

## Spatial Conversion Logic

### Early stage
The pair are still managing distance:
- who sits where
- who touches first
- who gives up space
- who pretends the room is not changing them

### Middle stage
The room starts reading them for each other:
- who notices shivering
- who watches breathing
- who stops pacing
- who begins to trust quiet

### Late stage
The room becomes impossible to treat as neutral:
- one silence matters too much
- one shared bed or couch changes the route permanently
- one act of care breaks the defensive structure

Useful generation rule:
- good forced-proximity routes escalate through micro-adjustments in space use

## What Weak Writing Gets Wrong

### 1. Confinement with no emotional effect
Weak writing traps the characters together and changes nothing important.

Reject that pattern.

### 2. Instant safety
Weak writing turns confinement into effortless coziness before the characters have earned it.

Reject that pattern.

### 3. Stress with no tenderness path
Weak writing makes the trap only irritating and never lets it become intimate.

Reject that pattern.

### 4. Heat with no safety logic
Weak writing jumps from close quarters to desire without showing whether the room feels dangerous or protective.

Reject that pattern.

## Practical Use In CharacterGen

### For `Scenario`
Use this file to decide:
- what trap locks the pair together
- whether the dominant route pressure is stress, heat, or safety growth
- when the room should feel hostile, awkward, protective, or charged
- whether the route is heading toward thaw or pressure-cooker release

### For `First Message Examples`
Prefer openings that imply:
- awareness of space
- irritation or care triggered by closeness
- body-level observation
- the room becoming part of the relationship logic

### For interactive route design
Use the variable logic to govern:
- when stress heightens the scene
- when safety begins to counterbalance confinement
- when a distance-locked branch should spike angst
- when physical closeness becomes undeniable

## CharacterGen Takeaway
Strong forced-proximity guidance should produce:
- rooms that actively shape the romance
- better closeness-through-pressure logic
- more believable thaw or explosion arcs

The target is not “there was only one bed.”
The target is a route where shared space becomes the thing neither character can keep pretending is neutral.
