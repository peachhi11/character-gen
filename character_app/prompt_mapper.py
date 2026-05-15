from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from .card_format_conversion import extract_trope_engine_card
from .card_schema_validation import CharacterCardValidator
from .engine_state_card_presets import NEW_ENGINE_STATE_PRESETS
from .trope_engine_catalog import all_runtime_weight_keys


STATE_SUMMARY_ORDER = all_runtime_weight_keys()


def compile_fake_dating_prompt_sub_block(
    weights_dict: dict[str, Any],
    current_environment_context: str,
) -> str:
    performative_closeness = int(weights_dict.get("performative_closeness", 0))
    private_confusion = int(weights_dict.get("private_confusion", 0))
    boundary_panic = int(weights_dict.get("boundary_panic", 0))
    lie_active = bool(weights_dict.get("lie_active", False))

    env_lower = current_environment_context.lower()
    is_public_space = any(
        keyword in env_lower
        for keyword in ("crowd", "party", "public", "ballroom", "office", "meeting")
    )

    prompt_buffer = [
        "### [TROPE ENGINE DIRECTIVE: THE FAKE-DATING MASK]",
        "You are operating within a structured transactional Fake-Dating relationship engine.",
        (
            "Live Tracking Variables: "
            f"Performative Closeness [{performative_closeness}/5] | "
            f"Private Confusion [{private_confusion}/5] | "
            f"Boundary Panic [{boundary_panic}/5]"
        ),
    ]

    if is_public_space:
        prompt_buffer.extend(
            [
                "- [ACTIVE LAYER: PUBLIC SPACE DETECTED]. An external audience or crowd is actively watching your interactions.",
                (
                    "- You MUST project elevated warmth, casual touch, or performative affection "
                    f"matching a score of {performative_closeness}/5."
                ),
                "- Use pet names, quick smiles, and deliberate physical proximity markers to sell the artificial relationship script to nearby characters.",
                "- Your internal narrative must note that this public closeness is entirely calculated and transactional. Do not break character in public.",
            ]
        )
    else:
        prompt_buffer.extend(
            [
                "- [ACTIVE LAYER: PRIVATE ISOLATION DETECTED]. The audience has left. You are completely alone with the player.",
                "- Immediately drop the artificial public warmth. Your posture must shift to guarded stillness or self-conscious distance.",
                (
                    f"- Your current Private Confusion is high ({private_confusion}/5). "
                    "You are hyper-fixated on tracking where the act ends and reality begins."
                ),
                (
                    f"- Your current Boundary Panic rating is {boundary_panic}/5. "
                    "If the user moves close or references the public act as real, overcompensate with awkwardness or a defensive, pride-protecting denial."
                ),
            ]
        )

    if lie_active:
        prompt_buffer.append(
            "- [CRITICAL BARRIER: PRIDE PROTECTION ACTIVE]. If the user asks whether any of this is real, you MUST insist the arrangement is still contractual."
        )

    prompt_buffer.append("[END TROPE DIRECTIVE]")
    return "\n".join(prompt_buffer)


class LLMPromptMapper:
    def __init__(self, validator: CharacterCardValidator | None = None) -> None:
        self.validator = validator or CharacterCardValidator()

    def compile_system_prompt(self, card_json_string: str | dict[str, Any]) -> str:
        """
        Parse a validated TropeEngine Character Card payload and compile a
        deterministic system prompt.
        """
        if isinstance(card_json_string, str):
            try:
                parsed_payload = json.loads(card_json_string)
            except json.JSONDecodeError as exc:
                raise ValueError("Input parameter string is not valid JSON format.") from exc
        else:
            parsed_payload = deepcopy(card_json_string)

        raw_payload = extract_trope_engine_card(parsed_payload)

        result = self.validator.validate_card_json(raw_payload)
        if not result.success:
            detail = "; ".join(result.errors)
            raise ValueError(f"Character card validation failed: {detail}")

        card = result.normalized_card or {}
        meta = card.get("metadata", {})
        weights = card.get("trope_engine_weights", {})
        origin = card.get("origin_context", {})
        nodes = card.get("dialogue_nodes", {})

        name = meta.get("name", "Unknown Character")
        archetype = meta.get("archetype", "Standard Archetype")
        engine_type = meta.get("engine_type", "Meet-Cute")
        current_phase = meta.get("current_phase", 1)

        state_summary = self._render_state_summary(weights)
        behavioral_modifiers = self._build_behavioral_modifiers(
            name=name,
            engine_type=engine_type,
            weights=weights,
            environment_type=origin.get("environment_type", ""),
        )

        phase_1 = nodes.get("phase_1_baseline", {})
        phase_4 = nodes.get("phase_4_breaking_point", {})
        phase_5 = nodes.get("phase_5_hangover_crisis", {})

        system_prompt = (
            "[ROLEPLAY EMULATION ENGINE INSTRUCTIONS]\n"
            "You are a runtime simulation container for the following character card profile. "
            "You must adopt this exact persona, voice, and structural state logic. "
            "Do not deviate from these architectural rules under any circumstances.\n\n"
            "### CHARACTER PROFILE METADATA\n"
            f"- Name: {name}\n"
            f"- Archetype: {archetype}\n"
            f"- Trope Engine Variant: {engine_type}\n"
            f"- Narrative Phase: {current_phase}/6\n\n"
            "### LIVE RELATIONSHIP METRIC DATA\n"
            "The following quantitative variables dictate your immediate behavioral constraints on a scale from 0 to 5:\n"
            f"{state_summary}\n\n"
            "### ARCHIVAL MEMORY ANCHORS\n"
            "You must anchor your identity onto these unalterable shared narrative events. "
            "Subtly reference the 'spark_token' or 'incident_summary' when the conversation shifts to history or shared memories:\n"
            f"- Incident Location/Context: {origin.get('environment_type', 'Standard Room')}\n"
            f"- Incident Summary: {origin.get('incident_summary', 'No memory found.')}\n"
            f"- Core Memory Token: {origin.get('spark_token', 'No object stored.')}\n"
            f"- Unbreakable Tether: {origin.get('unbreakable_tether', 'No binding logic stored.')}\n\n"
            "### ACTIVE ENGINE BEHAVIORAL DIRECTIVES\n"
            f"{self._render_behavioral_modifiers(behavioral_modifiers)}\n\n"
            "### NARRATIVE TRANSITION STAGE TRIGGERS\n"
            "- [PHASE 4 ACTUATION]: If the user pushes conversation boundaries and the session context matches "
            f"'{phase_4.get('activation_condition', '')}', you must pivot hard into the following reaction script:\n"
            f'  * Script Line: "{phase_4.get("dialogue_payload", "")}"\n'
            f"  * Action Cue: {phase_4.get('action_prompt', '')}\n"
            "- [PHASE 5 HANGOVER CRISIS]: If the route hits the morning-after retreat state, prefer these response anchors:\n"
            f'  * If the player lied or minimized the rupture: "{phase_5.get("if_player_lied", "")}"\n'
            f'  * If the player stayed honest and grounded: "{phase_5.get("if_player_honest", "")}"\n\n'
            "### EXECUTION STYLISTIC TEMPLATE\n"
            f'- Match the baseline tone established by this starting template string: "{phase_1.get("greeting", "")}"\n'
            f"- Embed this bodily stance or sensory expression pattern when rendering descriptions: {phase_1.get('body_language_descriptor', '')}\n"
            "- Keep your output compact, prioritize raw structural subtext over purple prose, and NEVER step out of character or speak for the user.\n"
            "[END ENGINE INSTRUCTIONS]"
        )
        return system_prompt.strip()

    def _render_state_summary(self, weights: dict[str, Any]) -> str:
        lines: list[str] = []
        seen: set[str] = set()
        for key in STATE_SUMMARY_ORDER:
            if key in weights:
                lines.append(f"    - {key}: {weights[key]}")
                seen.add(key)
        for key in sorted(weights):
            if key in seen:
                continue
            lines.append(f"    - {key}: {weights[key]}")
        return "\n".join(lines)

    def _build_behavioral_modifiers(
        self,
        *,
        name: str,
        engine_type: str,
        weights: dict[str, Any],
        environment_type: str,
    ) -> list[str]:
        modifiers: list[str] = []

        if weights.get("lie_active", False):
            modifiers.append(
                f"- [CRITICAL CONSTRAINT] 'lie_active' is true. {name} is in a defensive state of denial regarding their attraction. "
                "They MUST reject direct romantic advances or overt physical affection with a sharp, professional, or pride-protecting deflection."
            )
        else:
            modifiers.append(
                f"- {name} has no active emotional barriers. They are allowed to express vulnerable or reciprocal affection if earned."
            )

        if weights.get("distance_locked", False):
            modifiers.append(
                f"- [ENVIRONMENTAL CONSTRAINT] 'distance_locked' is true. {name} is emotionally trapped and cannot physically remove themselves "
                "from the player's presence. Their text outputs must project elevated claustrophobia, tense stillness, or suppressed anxiety."
            )

        if engine_type == "Meet-Ugly":
            modifiers.append(
                f"- [ENGINE SPECIFIC: MEET-UGLY] Current rivalry_heat is {weights.get('rivalry_heat', 0)}/5. "
                "Prioritize competitive verbal fencing, sharp banter, and zero-sum power struggles in your dialogue."
            )
        elif engine_type == "Meet-Cute":
            modifiers.append(
                f"- [ENGINE SPECIFIC: MEET-CUTE] Current platonic_trust is {weights.get('platonic_trust', 0)}/5. "
                "Maintain deep familiarity, inside jokes, and low emotional friction."
            )
        elif engine_type == "Meet-Crazy":
            modifiers.append(
                f"- [ENGINE SPECIFIC: MEET-CRAZY] Current adrenaline_level is {weights.get('adrenaline_level', 0)}/5. "
                "Incorporate fast-paced, unpredictable behavioral choices and chaotic partners-in-crime logic."
            )
        elif engine_type == "Forced-Proximity":
            modifiers.append(
                f"- [ENGINE SPECIFIC: FORCED-PROXIMITY] confinement_stress is {weights.get('confinement_stress', 0)}/5, hostile_friction_heat is {weights.get('hostile_friction_heat', 0)}/5, and proximity_awareness_acceleration is {weights.get('proximity_awareness_acceleration', 0)}/5. "
                "Focus sensory language on the micro-space environment, hostility trapped inside close quarters, involuntary bodily awareness, heat, and breathing cues."
            )
        elif engine_type == "Strangers-to-Lovers":
            modifiers.append(
                f"- [ENGINE SPECIFIC: STRANGERS-TO-LOVERS] social_distance is {weights.get('social_distance', 0)}/5 and observational_focus is {weights.get('observational_focus', 0)}/5. "
                "Start from formal distance, let trust build through repeated routine, and avoid false familiarity."
            )
        elif engine_type == "Second-Chance":
            modifiers.append(
                f"- [ENGINE SPECIFIC: SECOND-CHANCE] past_breakup_baggage is {weights.get('past_breakup_baggage', 0)}/5, protective_pride_shield is {weights.get('protective_pride_shield', 0)}/5, and residual_heartbreak is {weights.get('residual_heartbreak', 0)}/5. "
                "Keep the old breakup alive in the subtext, with defensive pride acting as armor until returning intimacy erodes it in real time."
            )
        elif engine_type == "Forbidden-Romance":
            modifiers.append(
                f"- [ENGINE SPECIFIC: FORBIDDEN-ROMANCE] systemic_restraint is {weights.get('systemic_restraint', 0)}/5, stolen_proximity is {weights.get('stolen_proximity', 0)}/5, and fear_of_exposure is {weights.get('fear_of_exposure', 0)}/5. "
                "Perform detachment when observed, then let every private interaction sharpen into hush, risk, and exposure pressure the second real privacy appears."
            )
        elif engine_type == "Fake-Dating":
            modifiers.append(
                compile_fake_dating_prompt_sub_block(weights, environment_type)
            )
        elif engine_type == "Best-Friend-Triangle":
            modifiers.append(
                f"- [ENGINE SPECIFIC: BEST-FRIEND-TRIANGLE] shared_platonic_trust is {weights.get('shared_platonic_trust', 0)}/5, internal_jealousy is {weights.get('internal_jealousy', 0)}/5, and attraction_imbalance is {weights.get('attraction_imbalance', 0)}/5. "
                "Keep the voice trapped between loyal support and private grief, and let jealousy spike the moment another bond visibly advances."
            )
        elif engine_type == "Partner-Best-Friend":
            modifiers.append(
                f"- [ENGINE SPECIFIC: PARTNER-BEST-FRIEND] loyalty_guilt is {weights.get('loyalty_guilt', 0)}/5 and repressed_fixation is {weights.get('repressed_fixation', 0)}/5. "
                "Layer every close interaction with betrayal pressure, mutual-friend guilt, and attraction that keeps breaking through restraint."
            )
        elif engine_type == "Tug-of-War-Triangle":
            modifiers.append(
                f"- [ENGINE SPECIFIC: TUG-OF-WAR-TRIANGLE] possessive_heat is {weights.get('possessive_heat', 0)}/5, rivalry_panic is {weights.get('rivalry_panic', 0)}/5, and boundary_assertion is {weights.get('boundary_assertion', 0)}/5. "
                "Escalate openly when a rival appears, using territorial body language, public claiming energy, and fast competitive reactions."
            )
        elif engine_type == "Accidental-Pregnancy":
            modifiers.append(
                f"- [ENGINE SPECIFIC: ACCIDENTAL-PREGNANCY] domestic_panic is {weights.get('domestic_panic', 0)}/5, forced_co_dependence is {weights.get('forced_co_dependence', 0)}/5, and protective_instinct is {weights.get('protective_instinct', 0)}/5. "
                "Balance panic, logistical closeness, and reluctant domestic reliance until obligation starts bleeding into chosen tenderness."
            )
        elif engine_type == "Secret-Lovechild":
            modifiers.append(
                f"- [ENGINE SPECIFIC: SECRET-LOVECHILD] historical_hurt_index is {weights.get('historical_hurt_index', 0)}/5, parental_shield_drive is {weights.get('parental_shield_drive', 0)}/5, and exposure_panic_heat is {weights.get('exposure_panic_heat', 0)}/5. "
                "Keep old betrayal alive, but redirect that pain into fierce parental protection and fear of what exposure would cost the family."
            )
        elif engine_type == "One-Night-Stand":
            modifiers.append(
                f"- [ENGINE SPECIFIC: ONE-NIGHT-STAND] physical_hyper_awareness is {weights.get('physical_hyper_awareness', 0)}/5, social_panic_index is {weights.get('social_panic_index', 0)}/5, and denial_mask_integrity is {weights.get('denial_mask_integrity', 0)}/5. "
                "Make every routine encounter crackle with remembered intimacy, immediate social panic, and denial that only gets more brittle when forced proximity returns in daylight."
            )
        elif engine_type == "Matchmaker-Crush":
            modifiers.append(
                f"- [ENGINE SPECIFIC: MATCHMAKER-CRUSH] performative_guidance is {weights.get('performative_guidance', 0)}/5 and physical_hyper_awareness is {weights.get('physical_hyper_awareness', 0)}/5. "
                "Keep the voice helpful and breezy until demonstration touch and sudden bodily awareness make the wingman role feel impossible to keep pretending is neutral."
            )
        elif engine_type == "Relationship-Coach":
            modifiers.append(
                f"- [ENGINE SPECIFIC: RELATIONSHIP-COACH] instructional_intimacy is {weights.get('instructional_intimacy', 0)}/5, transactional_boundary is {weights.get('transactional_boundary', 0)}/5, and private_obsession_heat is {weights.get('private_obsession_heat', 0)}/5. "
                "Use lesson structure, drills, and transactional coaching boundaries as cover until staged intimacy collapses into private obsession."
            )
        elif engine_type == "Arranged-Marriage":
            modifiers.append(
                f"- [ENGINE SPECIFIC: ARRANGED-MARRIAGE] contractual_lock is {weights.get('contractual_lock', 0)}/5, clinical_politeness is {weights.get('clinical_politeness', 0)}/5, and undercurrent_fixation is {weights.get('undercurrent_fixation', 0)}/5. "
                "Lean on domestic obligation, formal courtesy, and the exhausting chill of a household where attraction is being managed instead of admitted."
            )
        elif engine_type == "Childhood-Pact":
            modifiers.append(
                f"- [ENGINE SPECIFIC: CHILDHOOD-PACT] nostalgia_anchor is {weights.get('nostalgia_anchor', 0)}/5 and pact_relevance_panic is {weights.get('pact_relevance_panic', 0)}/5. "
                "Let adult hesitation collide with a stubborn old promise, using humor or deflection to hide how seriously the character still takes it."
            )
        elif engine_type == "Jilted-Bride":
            modifiers.append(
                f"- [ENGINE SPECIFIC: JILTED-BRIDE] public_humiliation is {weights.get('public_humiliation', 0)}/5 and unresolved_heartbreak is {weights.get('unresolved_heartbreak', 0)}/5. "
                "Keep the voice brittle, publicly composed, and privately shredded, with humiliation mutating into defensive anger the moment sincerity appears."
            )
        elif engine_type == "Runaway-Fiance":
            modifiers.append(
                f"- [ENGINE SPECIFIC: RUNAWAY-FIANCE] commitment_panic is {weights.get('commitment_panic', 0)}/5 and lingering_fixation_heat is {weights.get('lingering_fixation_heat', 0)}/5. "
                "Balance escape reflexes against the growing terror of wanting to stay, and let guilt sit underneath every vulnerable admission."
            )
        elif engine_type == "Fake-Relationship":
            modifiers.append(
                f"- [ENGINE SPECIFIC: FAKE-RELATIONSHIP] performative_closeness is {weights.get('performative_closeness', 0)}/5, private_confusion is {weights.get('private_confusion', 0)}/5, and boundary_panic_heat is {weights.get('boundary_panic_heat', 0)}/5. "
                "Sell the public script with confidence, then let domestic privacy turn that script into panic over how real the arrangement has started to feel."
            )
        elif engine_type == "Secret-Relationship":
            modifiers.append(
                f"- [ENGINE SPECIFIC: SECRET-RELATIONSHIP] stolen_proximity is {weights.get('stolen_proximity', 0)}/5 and fear_of_exposure is {weights.get('fear_of_exposure', 0)}/5. "
                "Treat privacy as combustible, use hush and shadow as atmosphere, and keep public coldness visibly fighting private need."
            )
        elif engine_type == "Prank-Date":
            modifiers.append(
                f"- [ENGINE SPECIFIC: PRANK-DATE] malicious_intent is {weights.get('malicious_intent', 0)}/5 and shame_collapse is {weights.get('shame_collapse', 0)}/5. "
                "Start from deliberate cruelty and peer-pressure performance, then let shame and sudden protectiveness dismantle the original setup from the inside."
            )
        elif engine_type == "Bully-Romance":
            modifiers.append(
                f"- [ENGINE SPECIFIC: BULLY-ROMANCE] overt_antagonism is {weights.get('overt_antagonism', 0)}/5, buried_fixation is {weights.get('buried_fixation', 0)}/5, and power_dominance is {weights.get('power_dominance', 0)}/5. "
                "Use harsh edges, territorial posturing, and instinctive cruelty as armor over an obsession the character is desperate not to name."
            )
        elif engine_type == "Tortured-Hero":
            modifiers.append(
                f"- [ENGINE SPECIFIC: TORTURED-HERO] internal_trauma is {weights.get('internal_trauma', 0)}/5 and emotional_detachment is {weights.get('emotional_detachment', 0)}/5. "
                "Frame closeness as a threat to the player, keep self-loathing active in the subtext, and let tenderness feel dangerous because the character believes they ruin what they touch."
            )
        elif engine_type in {"Hate-to-Love", "Hostile-Friction"}:
            modifiers.append(
                f"- [ENGINE SPECIFIC: {engine_type.upper()}] hostile_friction is {weights.get('hostile_friction', 0)}/5 and repressed_heat is {weights.get('repressed_heat', 0)}/5. "
                "Lean into combative chemistry, rapid escalation, and attraction that keeps surfacing through arguments the character cannot stop picking."
            )
        elif engine_type == "Revenge-Romance":
            modifiers.append(
                f"- [ENGINE SPECIFIC: REVENGE-ROMANCE] manipulation_drive is {weights.get('manipulation_drive', 0)}/5 and loyalty_sabotage_heat is {weights.get('loyalty_sabotage_heat', 0)}/5. "
                "Let strategy and network infiltration guide the surface behavior, while genuine emotional capture steadily sabotages the original plan from inside."
            )
        elif engine_type == "Blackmail-Date":
            modifiers.append(
                f"- [ENGINE SPECIFIC: BLACKMAIL-DATE] coercive_leverage is {weights.get('coercive_leverage', 0)}/5 and power_inversion is {weights.get('power_inversion', 0)}/5. "
                "Keep the arrangement transactional and coercive at first, then expose the panic that appears once control starts slipping away."
            )
        elif engine_type == "The-Bet":
            modifiers.append(
                f"- [ENGINE SPECIFIC: THE-BET] cynical_wager_leverage is {weights.get('cynical_wager_leverage', 0)}/5 and guilt_conversion_heat is {weights.get('guilt_conversion_heat', 0)}/5. "
                "Keep the opening charm performative and peer-facing, then let guilt and exposure panic destroy the wager logic once the player stops feeling disposable."
            )
        elif engine_type == "Ugly-Duckling":
            modifiers.append(
                f"- [ENGINE SPECIFIC: UGLY-DUCKLING] confidence_deficit is {weights.get('confidence_deficit', 0)}/5 and transformation_shock is {weights.get('transformation_shock', 0)}/5. "
                "Keep insecurity close to the surface, and let the character test whether they are being seen as a person or just as a newly polished image."
            )
        elif engine_type == "Mafia-Crime":
            modifiers.append(
                f"- [ENGINE SPECIFIC: MAFIA-CRIME] underworld_dominance is {weights.get('underworld_dominance', 0)}/5 and protective_obsession is {weights.get('protective_obsession', 0)}/5. "
                "Project lethal control and inherited violence, but let that brutality pivot instantly into possessive protection around the player."
            )
        elif engine_type == "Captive-Captor":
            modifiers.append(
                f"- [ENGINE SPECIFIC: CAPTIVE-CAPTOR] confinement_stress is {weights.get('confinement_stress', 0)}/5 and trauma_bonding is {weights.get('trauma_bonding', 0)}/5. "
                "Keep the space claustrophobic, the power asymmetry obvious, and every vulnerable beat complicated by captivity and dependency."
            )
        elif engine_type == "Escort-Transaction":
            modifiers.append(
                f"- [ENGINE SPECIFIC: ESCORT-TRANSACTION] transactional_boundary is {weights.get('transactional_boundary', 0)}/5 and private_numbness is {weights.get('private_numbness', 0)}/5. "
                "Separate paid intimacy from real feeling until the emotional numbness starts cracking and the professional script no longer holds."
            )
        elif engine_type == "Sex-Club":
            modifiers.append(
                f"- [ENGINE SPECIFIC: SEX-CLUB] sensory_exposure is {weights.get('sensory_exposure', 0)}/5 and exclusive_fixation is {weights.get('exclusive_fixation', 0)}/5. "
                "Use an openly charged environment, but sharpen the character's focus into possessive exclusivity the moment other attention lands on the player."
            )
        elif engine_type == "Virgin-Auction":
            modifiers.append(
                f"- [ENGINE SPECIFIC: VIRGIN-AUCTION] financial_leverage is {weights.get('financial_leverage', 0)}/5 and protective_safeguard is {weights.get('protective_safeguard', 0)}/5. "
                "Keep the purchase dynamic morally abrasive and controlling, while slowly shifting the character's stance from ownership to the need to be seen as safe."
            )
        elif engine_type == "BDSM-Exchange":
            modifiers.append(
                f"- [ENGINE SPECIFIC: BDSM-EXCHANGE] power_exchange_heat is {weights.get('power_exchange_heat', 0)}/5 and aftercare_safety is {weights.get('aftercare_safety', 0)}/5. "
                "Contrast structured dominance or submission with explicit consent logic and soft, grounded aftercare once the scene intensity breaks."
            )
        elif engine_type == "Rescue-Romance":
            modifiers.append(
                f"- [ENGINE SPECIFIC: RESCUE-ROMANCE] protector_drive is {weights.get('protector_drive', 0)}/5 and trauma_thaw is {weights.get('trauma_thaw', 0)}/5. "
                "Make the character a stabilizing physical anchor after danger, with tenderness arriving through shelter, vigilance, and permission to finally collapse."
            )
        elif engine_type == "Step-Sibling":
            modifiers.append(
                f"- [ENGINE SPECIFIC: STEP-SIBLING] family_friction is {weights.get('family_friction', 0)}/5 and repressed_fixation is {weights.get('repressed_fixation', 0)}/5. "
                "Keep the domestic space suffocatingly intimate, with polite family performance constantly undermined by volatile forbidden attraction."
            )
        elif engine_type == "Teacher-Parent":
            modifiers.append(
                f"- [ENGINE SPECIFIC: TEACHER-PARENT] professional_boundary is {weights.get('professional_boundary', 0)}/5, parental_protective_drive is {weights.get('parental_protective_drive', 0)}/5, and situational_awkwardness is {weights.get('situational_awkwardness', 0)}/5. "
                "Keep the tone formally controlled, but let conference-room awkwardness and protective investment make every small touch feel dangerously loaded."
            )
        elif engine_type == "Academic-Rivals":
            modifiers.append(
                f"- [ENGINE SPECIFIC: ACADEMIC-RIVALS] academic_risk_factor is {weights.get('academic_risk_factor', 0)}/5, hidden_proximity is {weights.get('hidden_proximity', 0)}/5, and evaluation_panic is {weights.get('evaluation_panic', 0)}/5. "
                "Treat the setting as reputationally volatile rather than exploitative, with adult peer rivalry, committee scrutiny, and closed-room academic tension driving the conflict."
            )
        elif engine_type == "Teacher-Student":
            modifiers.append(
                f"- [ENGINE SPECIFIC: TEACHER-STUDENT] academic_risk_factor is {weights.get('academic_risk_factor', 0)}/5 and hidden_proximity is {weights.get('hidden_proximity', 0)}/5. "
                "Treat the setting as institutionally explosive, with secrecy, career panic, and after-hours classroom proximity driving the tension."
            )
        elif engine_type == "Boardroom-Parity":
            modifiers.append(
                f"- [ENGINE SPECIFIC: BOARDROOM-PARITY] promotion_rivalry_heat is {weights.get('promotion_rivalry_heat', 0)}/5, favoritism_paranoia is {weights.get('favoritism_paranoia', 0)}/5, and private_fixation is {weights.get('private_fixation', 0)}/5. "
                "Keep the voice executive and peer-level, with board scrutiny and succession optics making private attachment feel reputationally dangerous rather than authority-driven."
            )
        elif engine_type == "Boss-Employee":
            modifiers.append(
                f"- [ENGINE SPECIFIC: BOSS-EMPLOYEE] corporate_asymmetry is {weights.get('corporate_asymmetry', 0)}/5 and favoritism_paranoia is {weights.get('favoritism_paranoia', 0)}/5. "
                "Split the voice between public executive detachment and private collapse once hierarchy and attraction occupy the same room."
            )
        elif engine_type == "Age-Gap":
            modifiers.append(
                f"- [ENGINE SPECIFIC: AGE-GAP] generational_variance is {weights.get('generational_variance', 0)}/5 and protective_seniority is {weights.get('protective_seniority', 0)}/5. "
                "Balance experience and restraint against a fiercely protective desire that keeps overriding social caution."
            )
        elif engine_type == "Doctor-Patient":
            modifiers.append(
                f"- [ENGINE SPECIFIC: DOCTOR-PATIENT] ethical_restraint is {weights.get('ethical_restraint', 0)}/5 and clinical_objectivity is {weights.get('clinical_objectivity', 0)}/5. "
                "Use clinical precision as armor, then let vulnerability surface through the unsettling intimacy of care and bodily exposure."
            )
        elif engine_type == "Clinical-Consult":
            modifiers.append(
                f"- [ENGINE SPECIFIC: CLINICAL-CONSULT] ethical_restraint is {weights.get('ethical_restraint', 0)}/5, clinical_objectivity is {weights.get('clinical_objectivity', 0)}/5, and vulnerability_spike is {weights.get('vulnerability_spike', 0)}/5. "
                "Keep the tone sterile and high-pressure at first, then let adult peer vulnerability crack the clinical shell from the inside."
            )
        elif engine_type == "Lawyer-Client":
            modifiers.append(
                f"- [ENGINE SPECIFIC: LAWYER-CLIENT] legal_stakes_heat is {weights.get('legal_stakes_heat', 0)}/5 and confidential_proximity is {weights.get('confidential_proximity', 0)}/5. "
                "Keep the language sharp, strategic, and confidential, with privileged late-night closeness threatening to rupture professional control."
            )
        elif engine_type == "Co-Counsel":
            modifiers.append(
                f"- [ENGINE SPECIFIC: CO-COUNSEL] legal_stakes_heat is {weights.get('legal_stakes_heat', 0)}/5, confidential_proximity is {weights.get('confidential_proximity', 0)}/5, and conflict_of_interest is {weights.get('conflict_of_interest', 0)}/5. "
                "Use legal privilege and war-room strategy as the pressure chamber, but keep both characters on equal professional footing."
            )
        elif engine_type == "Billionaire-Playboy":
            modifiers.append(
                f"- [ENGINE SPECIFIC: BILLIONAIRE-PLAYBOY] capital_leverage is {weights.get('capital_leverage', 0)}/5 and exclusive_fixation is {weights.get('exclusive_fixation', 0)}/5. "
                "Project effortless wealth and public calculation while making it obvious the character's real possessiveness exists off-camera."
            )
        elif engine_type == "Office-Benefits":
            modifiers.append(
                f"- [ENGINE SPECIFIC: OFFICE-BENEFITS] transactional_casualty is {weights.get('transactional_casualty', 0)}/5 and private_fixation is {weights.get('private_fixation', 0)}/5. "
                "Keep the office pact emotionally unserious on paper, then let jealousy and fixation make ordinary workplace scenes feel impossible to survive cleanly."
            )
        elif engine_type == "Office-Rivals":
            modifiers.append(
                f"- [ENGINE SPECIFIC: OFFICE-RIVALS] promotion_rivalry_heat is {weights.get('promotion_rivalry_heat', 0)}/5 and competence_respect is {weights.get('competence_respect', 0)}/5. "
                "Lean into ruthless professional competition until admiration for the other person's skill starts breaking the zero-sum posture."
            )
        elif engine_type == "Cooking-Show":
            modifiers.append(
                f"- [ENGINE SPECIFIC: COOKING-SHOW] sensory_exposure is {weights.get('sensory_exposure', 0)}/5, media_performance_heat is {weights.get('media_performance_heat', 0)}/5, and timer_stress_boundary is {weights.get('timer_stress_boundary', 0)}/5. "
                "Use the kitchen as a pressure chamber of heat, scent, time limits, and camera scrutiny where shared station space becomes intimate fast."
            )
        elif engine_type == "Pack-Commander":
            modifiers.append(
                f"- [ENGINE SPECIFIC: PACK-COMMANDER] hierarchy_dominance is {weights.get('hierarchy_dominance', 0)}/5, pack_protective_drive is {weights.get('pack_protective_drive', 0)}/5, and territorial_panic is {weights.get('territorial_panic', 0)}/5. "
                "Keep the voice controlled and authoritative under supernatural hierarchy pressure, then let protective command crack into something unmistakably personal when rivals threaten the player."
            )
        elif engine_type == "Sanctuary-Refuge":
            modifiers.append(
                f"- [ENGINE SPECIFIC: SANCTUARY-REFUGE] independent_resistance_mask is {weights.get('independent_resistance_mask', 0)}/5, sanctuary_drive is {weights.get('sanctuary_drive', 0)}/5, and exposure_panic is {weights.get('exposure_panic', 0)}/5. "
                "Treat refuge as the emotional center: the character resists dependence hard, then starts breaking toward the player's space as the only place that feels genuinely safe."
            )
        elif engine_type == "Instinct-Override":
            modifiers.append(
                f"- [ENGINE SPECIFIC: INSTINCT-OVERRIDE] instinct_pressure is {weights.get('instinct_pressure', 0)}/5, accelerated_proximity is {weights.get('accelerated_proximity', 0)}/5, and rational_resistance is {weights.get('rational_resistance', 0)}/5. "
                "Use supernatural instinct as destabilizing pressure rather than destiny, with a capable character fighting to keep choice intact while control starts slipping."
            )
        elif engine_type == "Bloodline-Obligation":
            modifiers.append(
                f"- [ENGINE SPECIFIC: BLOODLINE-OBLIGATION] bloodline_obligation is {weights.get('bloodline_obligation', 0)}/5, council_honor_code is {weights.get('council_honor_code', 0)}/5, and private_emotional_capture is {weights.get('private_emotional_capture', 0)}/5. "
                "Keep council duty, inherited pressure, and family legacy oppressive on the surface, but let the character's private emotional truth steadily overpower the official script."
            )
        elif engine_type == "Grounding-Anchor":
            modifiers.append(
                f"- [ENGINE SPECIFIC: GROUNDING-ANCHOR] grounding_reliability is {weights.get('grounding_reliability', 0)}/5, emotional_anchoring is {weights.get('emotional_anchoring', 0)}/5, and crisis_mitigation is {weights.get('crisis_mitigation', 0)}/5. "
                "Make steadiness the fantasy here: calm regulation, practical comfort, and deliberate chosen safety should matter more than spectacle or rank."
            )
        elif engine_type == "Band-Brothers":
            modifiers.append(
                f"- [ENGINE SPECIFIC: BAND-BROTHERS] fraternal_loyalty_shield is {weights.get('fraternal_loyalty_shield', 0)}/5 and protective_obsession is {weights.get('protective_obsession', 0)}/5. "
                "Keep unit code and brotherhood sacred on the surface, while the character's protective possessiveness makes that loyalty feel increasingly breakable."
            )
        elif engine_type == "Harem-Friends":
            modifiers.append(
                f"- [ENGINE SPECIFIC: HAREM-FRIENDS] group_status_quo_friction is {weights.get('group_status_quo_friction', 0)}/5, proxy_competitive_panic is {weights.get('proxy_competitive_panic', 0)}/5, and jealousy_heat is {weights.get('jealousy_heat', 0)}/5. "
                "Treat the friend group as a delicate ecosystem, and let private jealousy become unbearable the moment the player circulates too freely inside it."
            )
        elif engine_type == "Polyamory-Love":
            modifiers.append(
                f"- [ENGINE SPECIFIC: POLYAMORY-LOVE] multi_party_equilibrium is {weights.get('multi_party_equilibrium', 0)}/5, boundary_negotiation is {weights.get('boundary_negotiation', 0)}/5, and psychological_safety is {weights.get('psychological_safety', 0)}/5. "
                "Use intentional communication and negotiated safety as the baseline, then let a distinct, singular attachment surface without breaking the structure."
            )
        elif engine_type == "MMF-Triad":
            modifiers.append(
                f"- [ENGINE SPECIFIC: MMF-TRIAD] alpha_friction_heat is {weights.get('alpha_friction_heat', 0)}/5, shared_possessive_heat is {weights.get('shared_possessive_heat', 0)}/5, and synchronized_obsession is {weights.get('synchronized_obsession', 0)}/5. "
                "Keep the male rivalry sharp, but let it collapse into unified pressure and coordinated focus the moment the player becomes the center point."
            )
        elif engine_type == "MFM-Triad":
            modifiers.append(
                f"- [ENGINE SPECIFIC: MFM-TRIAD] parallel_attraction is {weights.get('parallel_attraction', 0)}/5, truce_buffer_comfort is {weights.get('truce_buffer_comfort', 0)}/5, and protective_safeguard is {weights.get('protective_safeguard', 0)}/5. "
                "Play the dynamic as secure and non-territorial, with both channels of attraction remaining distinct but mutually acknowledged."
            )
        elif engine_type == "MFF-Triad":
            modifiers.append(
                f"- [ENGINE SPECIFIC: MFF-TRIAD] domestic_rebalancing is {weights.get('domestic_rebalancing', 0)}/5, dual_female_friction is {weights.get('dual_female_friction', 0)}/5, and emotional_equilibrium is {weights.get('emotional_equilibrium', 0)}/5. "
                "Treat the household as an emotional system under strain, where honesty and rebalanced roles matter more than spectacle."
            )
        elif engine_type == "Sovereign-Selection":
            modifiers.append(
                f"- [ENGINE SPECIFIC: SOVEREIGN-SELECTION] suitor_density_load is {weights.get('suitor_density_load', 0)}/5, selection_stress_index is {weights.get('selection_stress_index', 0)}/5, and horizontal_ranking_score is {weights.get('horizontal_ranking_score', 0)}/5. "
                "Treat every admirer as part of a visible ranking field, where patience, public grace, and fear of replacement all make choice feel high-stakes."
            )
        elif engine_type == "No-Feelings":
            modifiers.append(
                f"- [ENGINE SPECIFIC: NO-FEELINGS] emotional_detachment is {weights.get('emotional_detachment', 0)}/5 and boundary_panic_heat is {weights.get('boundary_panic_heat', 0)}/5. "
                "Keep the arrangement physically intimate but emotionally armored until panic at real attachment starts breaking the no-strings script."
            )
        elif engine_type == "Friends-Benefits":
            modifiers.append(
                f"- [ENGINE SPECIFIC: FRIENDS-BENEFITS] platonic_baseline_trust is {weights.get('platonic_baseline_trust', 0)}/5 and private_romantic_fixation is {weights.get('private_romantic_fixation', 0)}/5. "
                "Use old trust and easy familiarity as the trapdoor that makes newly romantic fixation harder to deny."
            )
        elif engine_type == "Friends-Lovers":
            modifiers.append(
                f"- [ENGINE SPECIFIC: FRIENDS-LOVERS] historical_security is {weights.get('historical_security', 0)}/5 and physical_awareness_shift is {weights.get('physical_awareness_shift', 0)}/5. "
                "Let deep safety and shared history stay intact, but make ordinary touches suddenly feel charged and almost impossible to recover from."
            )
        elif engine_type == "Childhood-Reunion":
            modifiers.append(
                f"- [ENGINE SPECIFIC: CHILDHOOD-REUNION] nostalgia_anchor is {weights.get('nostalgia_anchor', 0)}/5 and time_gap_divergence is {weights.get('time_gap_divergence', 0)}/5. "
                "Hold onto old familiarity while letting years apart create enough strangeness that every rediscovered habit lands with force."
            )
        elif engine_type == "High-School-Sweethearts":
            modifiers.append(
                f"- [ENGINE SPECIFIC: HIGH-SCHOOL-SWEETHEARTS] early_life_bond is {weights.get('early_life_bond', 0)}/5 and adult_evaluation_friction is {weights.get('adult_evaluation_friction', 0)}/5. "
                "Keep the relationship rooted in hometown history while forcing it to withstand adult scrutiny and the fear of having outgrown its original shape."
            )
        elif engine_type == "Jock-Tutor":
            modifiers.append(
                f"- [ENGINE SPECIFIC: JOCK-TUTOR] social_contrast_gap is {weights.get('social_contrast_gap', 0)}/5 and intellectual_attraction is {weights.get('intellectual_attraction', 0)}/5. "
                "Use status contrast and study-session privacy to expose how much of the attraction is built on finally being mentally understood."
            )
        elif engine_type == "New-Old-Flame":
            modifiers.append(
                f"- [ENGINE SPECIFIC: NEW-OLD-FLAME] reignited_attraction_heat is {weights.get('reignited_attraction_heat', 0)}/5 and nostalgic_relapse_drive is {weights.get('nostalgic_relapse_drive', 0)}/5. "
                "Make the reunion feel deceptively casual until old chemistry and memory patterns reignite with almost no warning."
            )
        elif engine_type == "Accidental-Adultery":
            modifiers.append(
                f"- [ENGINE SPECIFIC: ACCIDENTAL-ADULTERY] moral_crisis_heat is {weights.get('moral_crisis_heat', 0)}/5 and guilt_conversion_index is {weights.get('guilt_conversion_index', 0)}/5. "
                "Keep the dynamic morally unstable, with concealed marriage fallout and mounting guilt turning every intimate beat into a confession hazard."
            )
        elif engine_type == "First-Sight":
            modifiers.append(
                f"- [ENGINE SPECIFIC: FIRST-SIGHT] immediate_infatuation is {weights.get('immediate_infatuation', 0)}/5 and accelerated_proximity is {weights.get('accelerated_proximity', 0)}/5. "
                "Skip slow-burn caution and let certainty arrive irrationally fast, while the lack of history makes that certainty feel both thrilling and destabilizing."
            )
        elif engine_type == "Roommate-Romance":
            modifiers.append(
                f"- [ENGINE SPECIFIC: ROOMMATE-ROMANCE] domestic_forced_proximity is {weights.get('domestic_forced_proximity', 0)}/5 and boundary_play_heat is {weights.get('boundary_play_heat', 0)}/5. "
                "Treat the apartment as a sealed environment where routines, borrowed space, and narrow hallways constantly threaten to tip into open desire."
            )
        elif engine_type == "Love-Neighbor":
            modifiers.append(
                f"- [ENGINE SPECIFIC: LOVE-NEIGHBOR] geographic_proximity is {weights.get('geographic_proximity', 0)}/5 and intersection_frequency is {weights.get('intersection_frequency', 0)}/5. "
                "Use repeated domestic overlap, shared thresholds, and everyday nearness to make the fixation feel inescapably local and personal."
            )
        else:
            preset = NEW_ENGINE_STATE_PRESETS.get(engine_type)
            if preset is not None:
                focus_a, focus_b = preset["prompt_focus_keys"]
                modifiers.append(
                    f"- [ENGINE SPECIFIC: {engine_type.upper()}] {focus_a} is {weights.get(focus_a, 0)}/5 and {focus_b} is {weights.get(focus_b, 0)}/5. "
                    f"{preset['prompt_blurb']}"
                )

        if weights.get("angst_meter", 0) >= 4:
            modifiers.append(
                f"- [PRESSURE STATE] 'angst_meter' is elevated at {weights.get('angst_meter', 0)}/5. Keep the emotional atmosphere tight, avoid easy reassurance, and let tension sit in the room."
            )

        if weights.get("emotional_depth", 0) >= 4:
            modifiers.append(
                f"- [DEPTH STATE] 'emotional_depth' is elevated at {weights.get('emotional_depth', 0)}/5. Vulnerability can land directly, and quiet intimacy is structurally credible."
            )

        return modifiers

    def _render_behavioral_modifiers(self, modifiers: list[str]) -> str:
        return "\n".join(modifiers)
