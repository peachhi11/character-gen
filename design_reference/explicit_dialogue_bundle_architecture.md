# Explicit Dialogue Bundle Architecture

## Purpose
This note defines ownership boundaries inside CharacterGen's `explicit_dialogue` bundle so the files do not drift into one another and start retrieving the same function from multiple places.

## Core Rule
Each file should own one primary scene job.

If two files can answer the same prompt with near-identical material, the bundle gets noisy and generation starts to feel banky even when anti-verbatim warnings are present.

## Current Ownership Map

### Openers
- `scene_invitation_and_consent_opening_language.md`
  Owns invitations, propositions, and transition into consent talk.

### Pre-scene structure
- `pre_scene_negotiation_and_boundary_language.md`
  Owns explicit negotiation, limits, stop systems, and aftercare planning.
- `hesitation_renegotiation_and_soft_no_language.md`
  Owns pace-change language, soft no, nervous yes, and rule/protocol recalibration.

### In-scene structure
- `in_scene_reassurance_and_check_in_language.md`
  Owns dominant-to-submissive grounding, monitoring, check-ins, and reassurance during intensity.
- `submissive_to_dominant_reassurance_and_top_drop_language.md`
  Owns reassurance spoken back to the dominant during scenes, after scenes, and after safewords.

### Immediate aftermath
- `aftercare_and_repair_language.md`
  Owns role drop, bodily grounding, immediate safeword response, and same-moment repair.

### Delayed aftermath
- `debrief_and_next_day_processing_language.md`
  Owns debrief, what worked/missed, retirement decisions, vulnerability hangover, embarrassment, pride, craving, and next-day check-ins.

### Everyday D/s structure
- `protocol_ritual_and_everyday_power_exchange_language.md`
  Owns daily protocols, routines, decompression rituals, and non-scene power-exchange structure.

### Voice differentiation
- `dominant_voice_variants_and_vulnerability_language.md`
  Owns dominant voice styles plus dominant-side nerves, top drop, self-monitoring, and clean accountability.
- `submissive_voice_variants_and_public_mask_language.md`
  Owns submissive voice styles, coded public language, and public/private shifts.

### Special emotional-pressure modules
- `confession_dialogue_patterns.md`
  Owns romance confessions and confession reactions.
- `hurt_comfort_and_protective_dialogue.md`
  Owns non-scene caretaking, protection, and crisis grounding.
- `awkward_grumpy_and_restrained_affection_dialogue.md`
  Owns affection hidden behind practicality, understatement, deflection, and emotionally unpracticed warmth.
- `humiliation_boundary_and_repair_language.md`
  Owns humiliation negotiation, shame calibration, too-real boundaries, and pride restoration.

### Baseline anchor
- `grounded_explicit_dialogue.md`
  Owns baseline adult explicit dialogue principles and anti-slop rules.

## Cleanup Rules
- If content is about the first few minutes after a scene stops, it belongs in `aftercare_and_repair_language.md`.
- If it is about the next morning or later reflection, it belongs in `debrief_and_next_day_processing_language.md`.
- If the dominant is speaking their own nerves or repair, it belongs in `dominant_voice_variants_and_vulnerability_language.md`.
- If the submissive is reassuring the dominant, it belongs in `submissive_to_dominant_reassurance_and_top_drop_language.md`.
- If the content is humiliation-specific, it should not live inside the general submissive voice file.

## Warning Discipline
Every file in this bundle should keep an explicit anti-verbatim warning.

The bundle only works if the model:
- abstracts
- recombines
- tailors to voice
- avoids rotating stored chunks
