from __future__ import annotations

import operator
import re

from .engine_state_card_presets import (
    NEW_ENGINE_STATE_PRESETS,
    legacy_origin_block_name,
)

BASE_WEIGHT_KEYS: tuple[str, ...] = (
    "angst_meter",
    "lie_active",
    "lie_count",
    "distance_locked",
)

ENGINE_REQUIRED_WEIGHTS: dict[str, tuple[str, ...]] = {
    "Meet-Cute": ("platonic_trust", "romantic_awareness"),
    "Meet-Ugly": ("rivalry_heat", "repressed_desire"),
    "Meet-Crazy": ("chaotic_chemistry", "adrenaline_level"),
    "Forced-Proximity": ("confinement_stress", "proximity_heat"),
    "Strangers-to-Lovers": (
        "social_distance",
        "observational_focus",
        "vulnerability_thaw",
    ),
    "Second-Chance": (
        "past_breakup_baggage",
        "protective_pride_shield",
        "residual_heartbreak",
    ),
    "Forbidden-Romance": (
        "systemic_restraint",
        "stolen_proximity",
        "fear_of_exposure",
    ),
    "Fake-Dating": (
        "performative_closeness",
        "private_confusion",
        "boundary_panic",
    ),
    "Best-Friend-Triangle": (
        "shared_platonic_trust",
        "internal_jealousy",
        "attraction_imbalance",
    ),
    "Partner-Best-Friend": (
        "loyalty_guilt",
        "forbidden_proximity",
        "repressed_fixation",
    ),
    "Tug-of-War-Triangle": (
        "possessive_heat",
        "rivalry_panic",
        "boundary_assertion",
    ),
    "Accidental-Pregnancy": (
        "domestic_panic",
        "forced_co_dependence",
        "protective_instinct",
    ),
    "Secret-Lovechild": (
        "historical_hurt_index",
        "parental_shield_drive",
        "exposure_panic_heat",
    ),
    "One-Night-Stand": (
        "physical_hyper_awareness",
        "social_awkwardness",
        "denial_buffer",
    ),
    "Matchmaker-Crush": (
        "performative_guidance",
        "proxy_resentment",
        "physical_hyper_awareness",
    ),
    "Relationship-Coach": (
        "instructional_proximity",
        "professional_restraint",
        "private_fixation",
    ),
    "Arranged-Marriage": (
        "contractual_lock",
        "clinical_politeness",
        "undercurrent_fixation",
    ),
    "Childhood-Pact": (
        "nostalgia_anchor",
        "pact_relevance_panic",
        "fear_of_rejection",
    ),
    "Jilted-Bride": (
        "public_humiliation",
        "unresolved_heartbreak",
        "defensive_anger",
    ),
    "Runaway-Fiance": (
        "commitment_panic",
        "abandonment_guilt",
        "lingering_fixation_heat",
    ),
    "Fake-Relationship": (
        "performative_closeness",
        "private_confusion",
        "boundary_panic_heat",
    ),
    "Secret-Relationship": (
        "systemic_restraint",
        "stolen_proximity",
        "fear_of_exposure",
    ),
    "Prank-Date": (
        "malicious_intent",
        "guilt_conversion",
        "genuine_fixation",
    ),
    "Bully-Romance": (
        "overt_antagonism",
        "buried_fixation",
        "power_dominance",
    ),
    "Tortured-Hero": (
        "internal_trauma",
        "emotional_detachment",
        "rescue_resistance",
    ),
    "Hate-to-Love": (
        "hostile_friction",
        "physical_attraction",
        "repressed_heat",
    ),
    "Revenge-Romance": (
        "manipulation_drive",
        "network_infiltration",
        "loyalty_sabotage_heat",
    ),
    "Blackmail-Date": (
        "coercive_leverage",
        "hostile_compliance",
        "power_inversion",
    ),
    "The-Bet": (
        "cynical_wager_leverage",
        "peer_validation_drive",
        "guilt_conversion_heat",
    ),
    "Ugly-Duckling": (
        "confidence_deficit",
        "transformation_shock",
        "fixated_observation",
    ),
    "Mafia-Crime": (
        "underworld_dominance",
        "lethal_risk_factor",
        "protective_obsession",
    ),
    "Captive-Captor": (
        "confinement_stress",
        "power_asymmetry",
        "trauma_bonding",
    ),
    "Escort-Transaction": (
        "transactional_boundary",
        "performative_intimacy",
        "private_numbness",
    ),
    "Sex-Club": (
        "sensory_exposure",
        "performative_heat",
        "exclusive_fixation",
    ),
    "Virgin-Auction": (
        "financial_leverage",
        "ownership_heat",
        "protective_safeguard",
    ),
    "BDSM-Exchange": (
        "power_exchange_heat",
        "consent_restraint",
        "aftercare_safety",
    ),
    "Rescue-Romance": (
        "protector_drive",
        "trauma_thaw",
        "vulnerability_spike",
    ),
    "Step-Sibling": (
        "domestic_lock",
        "family_friction",
        "repressed_fixation",
    ),
    "Teacher-Parent": (
        "professional_boundary",
        "parental_protective_drive",
        "situational_awkwardness",
    ),
    "Academic-Rivals": (
        "academic_risk_factor",
        "hidden_proximity",
        "evaluation_panic",
    ),
    "Teacher-Student": (
        "academic_risk_factor",
        "hidden_proximity",
        "evaluation_panic",
    ),
    "Boardroom-Parity": (
        "promotion_rivalry_heat",
        "favoritism_paranoia",
        "private_fixation",
    ),
    "Boss-Employee": (
        "corporate_asymmetry",
        "favoritism_paranoia",
        "private_fixation",
    ),
    "Age-Gap": (
        "generational_variance",
        "protective_seniority",
        "social_disapproval_heat",
    ),
    "Doctor-Patient": (
        "ethical_restraint",
        "clinical_objectivity",
        "vulnerability_spike",
    ),
    "Clinical-Consult": (
        "ethical_restraint",
        "clinical_objectivity",
        "vulnerability_spike",
    ),
    "Lawyer-Client": (
        "legal_stakes_heat",
        "confidential_proximity",
        "conflict_of_interest",
    ),
    "Co-Counsel": (
        "legal_stakes_heat",
        "confidential_proximity",
        "conflict_of_interest",
    ),
    "Billionaire-Playboy": (
        "capital_leverage",
        "media_scrutiny_heat",
        "exclusive_fixation",
    ),
    "Office-Benefits": (
        "transactional_casualty",
        "cubicle_proximity",
        "private_fixation",
    ),
    "Office-Rivals": (
        "promotion_rivalry_heat",
        "hostile_friction",
        "competence_respect",
    ),
    "Cooking-Show": (
        "sensory_exposure",
        "media_performance_heat",
        "timer_stress_boundary",
    ),
    "Pack-Commander": (
        "hierarchy_dominance",
        "pack_protective_drive",
        "territorial_panic",
    ),
    "Sanctuary-Refuge": (
        "independent_resistance_mask",
        "sanctuary_drive",
        "exposure_panic",
    ),
    "Instinct-Override": (
        "instinct_pressure",
        "accelerated_proximity",
        "rational_resistance",
    ),
    "Bloodline-Obligation": (
        "bloodline_obligation",
        "council_honor_code",
        "private_emotional_capture",
    ),
    "Grounding-Anchor": (
        "grounding_reliability",
        "emotional_anchoring",
        "crisis_mitigation",
    ),
    "Band-Brothers": (
        "fraternal_loyalty_shield",
        "tactical_proximity",
        "protective_obsession",
    ),
    "Harem-Friends": (
        "group_status_quo_friction",
        "proxy_competitive_panic",
        "jealousy_heat",
    ),
    "Polyamory-Love": (
        "multi_party_equilibrium",
        "boundary_negotiation",
        "psychological_safety",
    ),
    "MMF-Triad": (
        "alpha_friction_heat",
        "shared_possessive_heat",
        "synchronized_obsession",
    ),
    "MFM-Triad": (
        "parallel_attraction",
        "truce_buffer_comfort",
        "protective_safeguard",
    ),
    "MFF-Triad": (
        "domestic_rebalancing",
        "dual_female_friction",
        "emotional_equilibrium",
    ),
    "Sovereign-Selection": (
        "suitor_density_load",
        "selection_stress_index",
        "horizontal_ranking_score",
    ),
    "No-Feelings": (
        "emotional_detachment",
        "physical_hyper_awareness",
        "boundary_panic_heat",
    ),
    "Friends-Benefits": (
        "platonic_baseline_trust",
        "contractual_intimacy",
        "private_romantic_fixation",
    ),
    "Friends-Lovers": (
        "historical_security",
        "fear_of_relationship_loss",
        "physical_awareness_shift",
    ),
    "Childhood-Reunion": (
        "nostalgia_anchor",
        "time_gap_divergence",
        "stranger_awkwardness",
    ),
    "High-School-Sweethearts": (
        "early_life_bond",
        "hometown_environmental_anchor",
        "adult_evaluation_friction",
    ),
    "Jock-Tutor": (
        "social_contrast_gap",
        "forced_academic_proximity",
        "intellectual_attraction",
    ),
    "New-Old-Flame": (
        "reignited_attraction_heat",
        "nostalgic_relapse_drive",
        "lingering_romantic_fixation",
    ),
    "Accidental-Adultery": (
        "moral_crisis_heat",
        "hidden_marital_baggage",
        "guilt_conversion_index",
    ),
    "First-Sight": (
        "immediate_infatuation",
        "accelerated_proximity",
        "historical_baseline",
    ),
    "Roommate-Romance": (
        "domestic_forced_proximity",
        "shared_structural_overhead",
        "boundary_play_heat",
    ),
    "Shared-Utility-Boundary": (
        "domestic_forced_proximity",
        "shared_structural_overhead",
        "boundary_play_heat",
    ),
    "Love-Neighbor": (
        "geographic_proximity",
        "shared_property_boundary",
        "intersection_frequency",
    ),
}

ENGINE_REQUIRED_WEIGHTS.update(
    {
        engine_type: tuple(spec["required_weights"])
        for engine_type, spec in NEW_ENGINE_STATE_PRESETS.items()
    }
)

ENGINE_OPTION_ORDER: tuple[str, ...] = tuple(ENGINE_REQUIRED_WEIGHTS.keys())

OPTIONAL_ENGINE_WEIGHTS: dict[str, tuple[str, ...]] = {
    "Meet-Cute": ("fear_of_loss",),
    "Meet-Crazy": ("emotional_depth",),
    "BDSM-Exchange": ("safeword_breached",),
}

ENGINE_PHASE_FOUR_TRIGGER_RULES: dict[str, tuple[tuple[str, str, int], ...]] = {
    "Meet-Cute": (("romantic_tension", ">=", 4), ("romantic_awareness", ">=", 4)),
    "Meet-Ugly": (("repressed_desire", ">=", 4),),
    "Meet-Crazy": (("chaotic_chemistry", ">=", 4),),
    "Forced-Proximity": (("confinement_stress", ">=", 4),),
    "Strangers-to-Lovers": (("observational_focus", ">=", 4),),
    "Second-Chance": (
        ("residual_heartbreak", "<=", 1),
        ("protective_pride_shield", "<=", 1),
    ),
    "Forbidden-Romance": (("stolen_proximity", ">=", 4),),
    "Fake-Dating": (("private_confusion", ">=", 4),),
    "Best-Friend-Triangle": (("internal_jealousy", ">=", 4),),
    "Partner-Best-Friend": (("repressed_fixation", ">=", 4),),
    "Tug-of-War-Triangle": (("rivalry_panic", ">=", 4),),
    "Accidental-Pregnancy": (("forced_co_dependence", ">=", 5),),
    "Secret-Lovechild": (("parental_shield_drive", ">=", 5),),
    "One-Night-Stand": (("physical_hyper_awareness", ">=", 4),),
    "Matchmaker-Crush": (("physical_hyper_awareness", ">=", 4),),
    "Relationship-Coach": (("private_fixation", ">=", 4),),
    "Arranged-Marriage": (("undercurrent_fixation", ">=", 4),),
    "Childhood-Pact": (("pact_relevance_panic", ">=", 4),),
    "Jilted-Bride": (("unresolved_heartbreak", ">=", 5),),
    "Runaway-Fiance": (("lingering_fixation_heat", ">=", 4),),
    "Fake-Relationship": (("private_confusion", ">=", 4),),
    "Secret-Relationship": (("stolen_proximity", ">=", 4),),
    "Prank-Date": (("guilt_conversion", ">=", 4),),
    "Bully-Romance": (("buried_fixation", ">=", 4),),
    "Tortured-Hero": (("emotional_detachment", "<=", 1),),
    "Hate-to-Love": (("repressed_heat", ">=", 4),),
    "Revenge-Romance": (("loyalty_sabotage_heat", ">=", 4),),
    "Blackmail-Date": (("power_inversion", ">=", 4),),
    "The-Bet": ("guilt_conversion_heat >= 4 or peer_validation_drive == 5 and guilt_conversion_heat >= 3"),
    "Ugly-Duckling": (("transformation_shock", ">=", 4),),
    "Mafia-Crime": (("protective_obsession", ">=", 4),),
    "Captive-Captor": (("trauma_bonding", ">=", 4),),
    "Escort-Transaction": (("private_numbness", "<=", 1),),
    "Sex-Club": (("exclusive_fixation", ">=", 4),),
    "Virgin-Auction": (("protective_safeguard", ">=", 4),),
    "BDSM-Exchange": (("power_exchange_heat", ">=", 4),),
    "Rescue-Romance": (("trauma_thaw", ">=", 4),),
    "Step-Sibling": (("repressed_fixation", ">=", 4),),
    "Teacher-Parent": (("professional_boundary", "<=", 1),),
    "Academic-Rivals": (("hidden_proximity", ">=", 5),),
    "Teacher-Student": (("hidden_proximity", ">=", 5),),
    "Boardroom-Parity": (("private_fixation", ">=", 4),),
    "Boss-Employee": (("private_fixation", ">=", 4),),
    "Age-Gap": (("protective_seniority", ">=", 5),),
    "Doctor-Patient": (("clinical_objectivity", "<=", 1),),
    "Clinical-Consult": (("clinical_objectivity", "<=", 1),),
    "Lawyer-Client": (("confidential_proximity", ">=", 5),),
    "Co-Counsel": (("confidential_proximity", ">=", 5),),
    "Billionaire-Playboy": (("exclusive_fixation", ">=", 4),),
    "Office-Benefits": (("private_fixation", ">=", 4),),
    "Office-Rivals": (("competence_respect", ">=", 4),),
    "Cooking-Show": (("sensory_exposure", ">=", 4),),
    "Pack-Commander": (("territorial_panic", ">=", 4),),
    "Sanctuary-Refuge": (("sanctuary_drive", ">=", 4), ("exposure_panic", ">=", 4)),
    "Instinct-Override": (("rational_resistance", "<=", 1),),
    "Bloodline-Obligation": (("private_emotional_capture", ">=", 4),),
    "Grounding-Anchor": (("grounding_reliability", ">=", 5), ("crisis_mitigation", ">=", 4)),
    "Band-Brothers": (("protective_obsession", ">=", 4),),
    "Harem-Friends": (("jealousy_heat", ">=", 4),),
    "Polyamory-Love": (("boundary_negotiation", "<=", 1),),
    "MMF-Triad": (("synchronized_obsession", ">=", 4),),
    "MFM-Triad": (("parallel_attraction", ">=", 4),),
    "MFF-Triad": (("domestic_rebalancing", ">=", 4),),
    "Sovereign-Selection": (("selection_stress_index", ">=", 4),),
    "No-Feelings": (("boundary_panic_heat", ">=", 4),),
    "Friends-Benefits": (("private_romantic_fixation", ">=", 4),),
    "Friends-Lovers": (("physical_awareness_shift", ">=", 4),),
    "Childhood-Reunion": (("time_gap_divergence", "<=", 1),),
    "High-School-Sweethearts": (("adult_evaluation_friction", ">=", 4),),
    "Jock-Tutor": (("intellectual_attraction", ">=", 4),),
    "New-Old-Flame": (("nostalgic_relapse_drive", ">=", 4),),
    "Accidental-Adultery": (("guilt_conversion_index", ">=", 4),),
    "First-Sight": (("accelerated_proximity", ">=", 4),),
    "Roommate-Romance": (("boundary_play_heat", ">=", 4),),
    "Shared-Utility-Boundary": (("boundary_play_heat", ">=", 4),),
    "Love-Neighbor": (("intersection_frequency", ">=", 4),),
}


_PHASE_FOUR_EXPR_PARSER = re.compile(
    r"([a-zA-Z_][a-zA-Z0-9_]*)\s*(>=|<=|==|!=|>|<)\s*(\d+)"
)
_PHASE_FOUR_OPERATORS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
    "!=": operator.ne,
}


def _preset_phase_four_rules(
    phase_four_rule: str | tuple[str, str, int] | tuple[tuple[str, str, int], ...]
) -> tuple[tuple[str, str, int], ...]:
    if isinstance(phase_four_rule, str):
        return tuple(
            (key, operator, int(threshold))
            for key, operator, threshold in _PHASE_FOUR_EXPR_PARSER.findall(
                phase_four_rule
            )
        )
    if phase_four_rule and isinstance(phase_four_rule[0], tuple):
        return tuple(phase_four_rule)
    return (tuple(phase_four_rule),)


ENGINE_PHASE_FOUR_TRIGGER_RULES.update(
    {
        engine_type: _preset_phase_four_rules(spec["phase_four_rule"])
        for engine_type, spec in NEW_ENGINE_STATE_PRESETS.items()
    }
)

ENGINE_PHASE_FOUR_TRIGGER_KEYS: dict[str, set[str]] = {
    engine_type: {key for key, _operator, _threshold in rules}
    for engine_type, rules in ENGINE_PHASE_FOUR_TRIGGER_RULES.items()
}


def phase_four_activation_condition(engine_type: str) -> str:
    if engine_type in NEW_ENGINE_STATE_PRESETS:
        return str(
            NEW_ENGINE_STATE_PRESETS[engine_type]["dialogue_nodes"][
                "phase_4_breaking_point"
            ]["activation_condition"]
        )
    rules = ENGINE_PHASE_FOUR_TRIGGER_RULES.get(engine_type, ())
    if not rules:
        return "True"
    return " or ".join(
        f"{key} {operator} {threshold}" for key, operator, threshold in rules
    )

LEGACY_ORIGIN_BLOCKS: dict[str, tuple[str, ...]] = {
    "Meet-Cute": ("meet_cute_origin",),
    "Meet-Ugly": ("meet_ugly_origin",),
    "Meet-Crazy": ("meet_crazy_origin", "meet_context"),
    "Forced-Proximity": ("forced_proximity_origin",),
    "Strangers-to-Lovers": ("strangers_to_lovers_origin",),
    "Second-Chance": ("second_chance_origin",),
    "Forbidden-Romance": ("forbidden_romance_origin",),
    "Fake-Dating": ("fake_dating_origin",),
    "Best-Friend-Triangle": ("best_friend_triangle_origin",),
    "Partner-Best-Friend": ("partner_best_friend_origin",),
    "Tug-of-War-Triangle": ("tug_of_war_triangle_origin",),
    "Accidental-Pregnancy": ("accidental_pregnancy_origin",),
    "Secret-Lovechild": ("secret_lovechild_origin",),
    "One-Night-Stand": ("one_night_stand_origin",),
    "Matchmaker-Crush": ("matchmaker_crush_origin",),
    "Relationship-Coach": ("relationship_coach_origin",),
    "Arranged-Marriage": ("arranged_marriage_origin",),
    "Childhood-Pact": ("childhood_pact_origin",),
    "Jilted-Bride": ("jilted_bride_origin",),
    "Runaway-Fiance": ("runaway_fiance_origin",),
    "Fake-Relationship": ("fake_relationship_origin",),
    "Secret-Relationship": ("secret_relationship_origin",),
    "Prank-Date": ("prank_date_origin",),
    "Bully-Romance": ("bully_romance_origin",),
    "Tortured-Hero": ("tortured_hero_origin",),
    "Hate-to-Love": ("hate_to_love_origin",),
    "Revenge-Romance": ("revenge_romance_origin",),
    "Blackmail-Date": ("blackmail_date_origin",),
    "The-Bet": ("the_bet_origin",),
    "Ugly-Duckling": ("ugly_duckling_origin",),
    "Mafia-Crime": ("mafia_crime_origin",),
    "Captive-Captor": ("captive_captor_origin",),
    "Escort-Transaction": ("escort_transaction_origin",),
    "Sex-Club": ("sex_club_origin",),
    "Virgin-Auction": ("virgin_auction_origin",),
    "BDSM-Exchange": ("bdsm_exchange_origin",),
    "Rescue-Romance": ("rescue_romance_origin",),
    "Step-Sibling": ("step_sibling_origin",),
    "Teacher-Parent": ("teacher_parent_origin",),
    "Academic-Rivals": ("academic_rivals_origin",),
    "Teacher-Student": ("teacher_student_origin",),
    "Boardroom-Parity": ("boardroom_parity_origin",),
    "Boss-Employee": ("boss_employee_origin",),
    "Age-Gap": ("age_gap_origin",),
    "Doctor-Patient": ("doctor_patient_origin",),
    "Clinical-Consult": ("clinical_consult_origin",),
    "Lawyer-Client": ("lawyer_client_origin",),
    "Co-Counsel": ("co_counsel_origin",),
    "Billionaire-Playboy": ("billionaire_playboy_origin",),
    "Office-Benefits": ("office_benefits_origin",),
    "Office-Rivals": ("office_rivals_origin",),
    "Cooking-Show": ("cooking_show_origin",),
    "Pack-Commander": ("pack_commander_origin",),
    "Sanctuary-Refuge": ("sanctuary_refuge_origin",),
    "Instinct-Override": ("instinct_override_origin",),
    "Bloodline-Obligation": ("bloodline_obligation_origin",),
    "Grounding-Anchor": ("grounding_anchor_origin",),
    "Band-Brothers": ("band_brothers_origin",),
    "Harem-Friends": ("harem_friends_origin",),
    "Polyamory-Love": ("polyamory_love_origin",),
    "MMF-Triad": ("mmf_triad_origin",),
    "MFM-Triad": ("mfm_triad_origin",),
    "MFF-Triad": ("mff_triad_origin",),
    "No-Feelings": ("no_feelings_origin",),
    "Friends-Benefits": ("friends_benefits_origin",),
    "Friends-Lovers": ("friends_lovers_origin",),
    "Childhood-Reunion": ("childhood_reunion_origin",),
    "High-School-Sweethearts": ("high_school_sweethearts_origin",),
    "Jock-Tutor": ("jock_tutor_origin",),
    "New-Old-Flame": ("new_old_flame_origin",),
    "Accidental-Adultery": ("accidental_adultery_origin",),
    "First-Sight": ("first_sight_origin",),
    "Roommate-Romance": ("roommate_romance_origin",),
    "Shared-Utility-Boundary": ("shared_utility_boundary_origin",),
    "Love-Neighbor": ("love_neighbor_origin",),
}

LEGACY_ORIGIN_BLOCKS.update(
    {
        engine_type: (legacy_origin_block_name(engine_type),)
        for engine_type in NEW_ENGINE_STATE_PRESETS
    }
)

LEGACY_ORIGIN_TO_CANONICAL: dict[str, dict[str, str]] = {
    "Meet-Cute": {
        "type": "environment_type",
        "incident": "incident_summary",
        "spark_token": "spark_token",
        "tether": "unbreakable_tether",
    },
    "Meet-Ugly": {
        "type": "environment_type",
        "incident": "incident_summary",
        "spark_token": "spark_token",
        "tether": "unbreakable_tether",
    },
    "Meet-Crazy": {
        "type": "environment_type",
        "spectacle": "incident_summary",
        "token": "spark_token",
        "lock": "unbreakable_tether",
    },
    "Forced-Proximity": {
        "type": "environment_type",
        "trap": "incident_summary",
        "pressure_token": "spark_token",
        "release_trigger": "unbreakable_tether",
    },
    "Strangers-to-Lovers": {
        "type": "environment_type",
        "routine": "incident_summary",
        "observation_token": "spark_token",
        "intersection": "unbreakable_tether",
    },
    "Second-Chance": {
        "type": "environment_type",
        "history": "incident_summary",
        "relic": "spark_token",
        "promise": "unbreakable_tether",
    },
    "Forbidden-Romance": {
        "type": "environment_type",
        "risk": "incident_summary",
        "cover_story": "spark_token",
        "rule": "unbreakable_tether",
    },
    "Fake-Dating": {
        "type": "environment_type",
        "contract": "incident_summary",
        "prop": "spark_token",
        "public_hook": "unbreakable_tether",
    },
    "Best-Friend-Triangle": {
        "type": "environment_type",
        "triangle_pressure": "incident_summary",
        "keepsake": "spark_token",
        "shared_history": "unbreakable_tether",
    },
    "Partner-Best-Friend": {
        "type": "environment_type",
        "loyalty_breach": "incident_summary",
        "cover_token": "spark_token",
        "mutual_connection": "unbreakable_tether",
    },
    "Tug-of-War-Triangle": {
        "type": "environment_type",
        "rival_entry": "incident_summary",
        "claim_marker": "spark_token",
        "competitive_link": "unbreakable_tether",
    },
    "Accidental-Pregnancy": {
        "type": "environment_type",
        "domestic_shock": "incident_summary",
        "ultrasound_token": "spark_token",
        "shared_obligation": "unbreakable_tether",
    },
    "Secret-Lovechild": {
        "type": "environment_type",
        "buried_history": "incident_summary",
        "family_relic": "spark_token",
        "hidden_bond": "unbreakable_tether",
    },
    "One-Night-Stand": {
        "type": "environment_type",
        "morning_after": "incident_summary",
        "forgotten_item": "spark_token",
        "recurring_intersection": "unbreakable_tether",
    },
    "Matchmaker-Crush": {
        "type": "environment_type",
        "proxy_plan": "incident_summary",
        "date_note": "spark_token",
        "advisor_role": "unbreakable_tether",
    },
    "Relationship-Coach": {
        "type": "environment_type",
        "practice_drill": "incident_summary",
        "lesson_token": "spark_token",
        "training_contract": "unbreakable_tether",
    },
    "Arranged-Marriage": {
        "type": "environment_type",
        "contract": "incident_summary",
        "marital_symbol": "spark_token",
        "household_lock": "unbreakable_tether",
    },
    "Childhood-Pact": {
        "type": "environment_type",
        "old_promise": "incident_summary",
        "kept_note": "spark_token",
        "nostalgic_tether": "unbreakable_tether",
    },
    "Jilted-Bride": {
        "type": "environment_type",
        "wedding_ruin": "incident_summary",
        "keepsake": "spark_token",
        "broken_vow": "unbreakable_tether",
    },
    "Runaway-Fiance": {
        "type": "environment_type",
        "escape": "incident_summary",
        "suitcase_tag": "spark_token",
        "unfinished_vow": "unbreakable_tether",
    },
    "Fake-Relationship": {
        "type": "environment_type",
        "public_script": "incident_summary",
        "prop": "spark_token",
        "cover_story": "unbreakable_tether",
    },
    "Secret-Relationship": {
        "type": "environment_type",
        "risk": "incident_summary",
        "cover_token": "spark_token",
        "buried_rule": "unbreakable_tether",
    },
    "Prank-Date": {
        "type": "environment_type",
        "dare": "incident_summary",
        "receipt": "spark_token",
        "fallout": "unbreakable_tether",
    },
    "Bully-Romance": {
        "type": "environment_type",
        "power_play": "incident_summary",
        "target_marker": "spark_token",
        "schoolyard_tether": "unbreakable_tether",
    },
    "Tortured-Hero": {
        "type": "environment_type",
        "wound": "incident_summary",
        "scar_token": "spark_token",
        "rescue_tether": "unbreakable_tether",
    },
    "Hate-to-Love": {
        "type": "environment_type",
        "collision": "incident_summary",
        "friction_token": "spark_token",
        "forced_overlap": "unbreakable_tether",
    },
    "Revenge-Romance": {
        "type": "environment_type",
        "plot": "incident_summary",
        "evidence": "spark_token",
        "target_link": "unbreakable_tether",
    },
    "Blackmail-Date": {
        "type": "environment_type",
        "secret": "incident_summary",
        "leverage_token": "spark_token",
        "compliance_chain": "unbreakable_tether",
    },
    "The-Bet": {
        "type": "environment_type",
        "wager": "incident_summary",
        "group_chat_receipt": "spark_token",
        "public_stakes": "unbreakable_tether",
    },
    "Ugly-Duckling": {
        "type": "environment_type",
        "reinvention": "incident_summary",
        "old_photo": "spark_token",
        "recognition_tether": "unbreakable_tether",
    },
    "Mafia-Crime": {
        "type": "environment_type",
        "syndicate_pressure": "incident_summary",
        "family_token": "spark_token",
        "blood_oath": "unbreakable_tether",
    },
    "Captive-Captor": {
        "type": "environment_type",
        "captivity": "incident_summary",
        "cell_key": "spark_token",
        "isolation_chain": "unbreakable_tether",
    },
    "Escort-Transaction": {
        "type": "environment_type",
        "arrangement": "incident_summary",
        "ledger_token": "spark_token",
        "paid_boundary": "unbreakable_tether",
    },
    "Sex-Club": {
        "type": "environment_type",
        "venue_heat": "incident_summary",
        "collar_token": "spark_token",
        "exclusive_claim": "unbreakable_tether",
    },
    "Virgin-Auction": {
        "type": "environment_type",
        "sale": "incident_summary",
        "contract_token": "spark_token",
        "purchase_chain": "unbreakable_tether",
    },
    "BDSM-Exchange": {
        "type": "environment_type",
        "scene": "incident_summary",
        "safeword_token": "spark_token",
        "aftercare_bond": "unbreakable_tether",
    },
    "Rescue-Romance": {
        "type": "environment_type",
        "crisis": "incident_summary",
        "comfort_token": "spark_token",
        "shelter_tether": "unbreakable_tether",
    },
    "Step-Sibling": {
        "type": "environment_type",
        "household_tension": "incident_summary",
        "family_photo": "spark_token",
        "domestic_tether": "unbreakable_tether",
    },
    "Teacher-Parent": {
        "type": "environment_type",
        "conference": "incident_summary",
        "report_token": "spark_token",
        "district_rule": "unbreakable_tether",
    },
    "Academic-Rivals": {
        "type": "environment_type",
        "seminar_after_hours": "incident_summary",
        "faculty_key": "spark_token",
        "committee_chain": "unbreakable_tether",
    },
    "Teacher-Student": {
        "type": "environment_type",
        "after_hours": "incident_summary",
        "syllabus_token": "spark_token",
        "institutional_rule": "unbreakable_tether",
    },
    "Boardroom-Parity": {
        "type": "environment_type",
        "board_review": "incident_summary",
        "access_badge": "spark_token",
        "investor_chain": "unbreakable_tether",
    },
    "Boss-Employee": {
        "type": "environment_type",
        "promotion": "incident_summary",
        "lanyard_token": "spark_token",
        "boardroom_chain": "unbreakable_tether",
    },
    "Age-Gap": {
        "type": "environment_type",
        "judgment": "incident_summary",
        "generation_token": "spark_token",
        "future_pull": "unbreakable_tether",
    },
    "Doctor-Patient": {
        "type": "environment_type",
        "consult": "incident_summary",
        "chart_token": "spark_token",
        "oath": "unbreakable_tether",
    },
    "Clinical-Consult": {
        "type": "environment_type",
        "clinical_consult": "incident_summary",
        "consult_clipboard": "spark_token",
        "ward_tether": "unbreakable_tether",
    },
    "Lawyer-Client": {
        "type": "environment_type",
        "deposition": "incident_summary",
        "brief_token": "spark_token",
        "privilege": "unbreakable_tether",
    },
    "Co-Counsel": {
        "type": "environment_type",
        "war_room": "incident_summary",
        "tie_token": "spark_token",
        "privilege_wall": "unbreakable_tether",
    },
    "Billionaire-Playboy": {
        "type": "environment_type",
        "media_circus": "incident_summary",
        "tabloid_token": "spark_token",
        "capital_chain": "unbreakable_tether",
    },
    "Office-Benefits": {
        "type": "environment_type",
        "pact": "incident_summary",
        "breakroom_token": "spark_token",
        "workplace_overlap": "unbreakable_tether",
    },
    "Office-Rivals": {
        "type": "environment_type",
        "promotion_war": "incident_summary",
        "account_token": "spark_token",
        "shared_deadline": "unbreakable_tether",
    },
    "Cooking-Show": {
        "type": "environment_type",
        "station_pressure": "incident_summary",
        "kitchen_token": "spark_token",
        "camera_timer": "unbreakable_tether",
    },
    "Pack-Commander": {
        "type": "environment_type",
        "pack_challenge": "incident_summary",
        "command_sigil": "spark_token",
        "council_chain": "unbreakable_tether",
    },
    "Sanctuary-Refuge": {
        "type": "environment_type",
        "lockdown": "incident_summary",
        "ward_stone": "spark_token",
        "safehouse_rule": "unbreakable_tether",
    },
    "Instinct-Override": {
        "type": "environment_type",
        "breach": "incident_summary",
        "monitor_charm": "spark_token",
        "override_lock": "unbreakable_tether",
    },
    "Bloodline-Obligation": {
        "type": "environment_type",
        "council_vote": "incident_summary",
        "succession_charter": "spark_token",
        "legacy_chain": "unbreakable_tether",
    },
    "Grounding-Anchor": {
        "type": "environment_type",
        "panic_spiral": "incident_summary",
        "tea_token": "spark_token",
        "safe_anchor": "unbreakable_tether",
    },
    "Band-Brothers": {
        "type": "environment_type",
        "unit_code": "incident_summary",
        "dog_tag": "spark_token",
        "battle_tether": "unbreakable_tether",
    },
    "Harem-Friends": {
        "type": "environment_type",
        "group_circle": "incident_summary",
        "inside_joke": "spark_token",
        "friend_group_lock": "unbreakable_tether",
    },
    "Polyamory-Love": {
        "type": "environment_type",
        "boundary_talk": "incident_summary",
        "agreement_token": "spark_token",
        "shared_structure": "unbreakable_tether",
    },
    "MMF-Triad": {
        "type": "environment_type",
        "rival_sync": "incident_summary",
        "claim_token": "spark_token",
        "closed_exit": "unbreakable_tether",
    },
    "MFM-Triad": {
        "type": "environment_type",
        "truce": "incident_summary",
        "center_space": "spark_token",
        "shared_invitation": "unbreakable_tether",
    },
    "MFF-Triad": {
        "type": "environment_type",
        "household_shift": "incident_summary",
        "bedroom_token": "spark_token",
        "domestic_system": "unbreakable_tether",
    },
    "Sovereign-Selection": {
        "type": "environment_type",
        "selection_field": "incident_summary",
        "rival_cards": "spark_token",
        "ranking_pressure": "unbreakable_tether",
    },
    "No-Feelings": {
        "type": "environment_type",
        "casual_rule": "incident_summary",
        "keyring_token": "spark_token",
        "morning_exit": "unbreakable_tether",
    },
    "Friends-Benefits": {
        "type": "environment_type",
        "arrangement": "incident_summary",
        "friendship_token": "spark_token",
        "casual_contract": "unbreakable_tether",
    },
    "Friends-Lovers": {
        "type": "environment_type",
        "confession_delay": "incident_summary",
        "comfort_token": "spark_token",
        "anchor_bond": "unbreakable_tether",
    },
    "Childhood-Reunion": {
        "type": "environment_type",
        "reunion": "incident_summary",
        "arcade_photo": "spark_token",
        "missing_years": "unbreakable_tether",
    },
    "High-School-Sweethearts": {
        "type": "environment_type",
        "bleacher_promise": "incident_summary",
        "class_ring": "spark_token",
        "hometown_pull": "unbreakable_tether",
    },
    "Jock-Tutor": {
        "type": "environment_type",
        "study_session": "incident_summary",
        "notebook_token": "spark_token",
        "grade_pressure": "unbreakable_tether",
    },
    "New-Old-Flame": {
        "type": "environment_type",
        "coffee_reunion": "incident_summary",
        "old_song": "spark_token",
        "embers": "unbreakable_tether",
    },
    "Accidental-Adultery": {
        "type": "environment_type",
        "buried_marriage": "incident_summary",
        "ring_token": "spark_token",
        "paperwork_chain": "unbreakable_tether",
    },
    "First-Sight": {
        "type": "environment_type",
        "first_glance": "incident_summary",
        "crowd_token": "spark_token",
        "trajectory_shift": "unbreakable_tether",
    },
    "Roommate-Romance": {
        "type": "environment_type",
        "lease": "incident_summary",
        "hallway_token": "spark_token",
        "shared_roof": "unbreakable_tether",
    },
    "Shared-Utility-Boundary": {
        "type": "environment_type",
        "utility_split": "incident_summary",
        "spare_key": "spark_token",
        "shared_household": "unbreakable_tether",
    },
    "Love-Neighbor": {
        "type": "environment_type",
        "mailbox_meeting": "incident_summary",
        "shared_wall": "spark_token",
        "threshold_pull": "unbreakable_tether",
    },
}

LEGACY_ORIGIN_TO_CANONICAL.update(
    {
        engine_type: dict(spec["legacy_aliases"])
        for engine_type, spec in NEW_ENGINE_STATE_PRESETS.items()
    }
)


def phase_four_trigger_satisfied(
    engine_type: str,
    weights: dict[str, object],
    *,
    metric_key: str | None = None,
) -> bool:
    preset = NEW_ENGINE_STATE_PRESETS.get(engine_type)
    if preset is not None:
        condition = str(
            preset["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ]
        ).strip()
        if metric_key is not None and metric_key not in ENGINE_PHASE_FOUR_TRIGGER_KEYS.get(
            engine_type, set()
        ):
            return False
        if condition and (" or " in condition.lower() or " and " in condition.lower()):
            return _evaluate_phase_four_condition(condition, weights)

    for key, operator, threshold in ENGINE_PHASE_FOUR_TRIGGER_RULES.get(engine_type, ()):
        if metric_key is not None and key != metric_key:
            continue
        value = weights.get(key)
        if isinstance(value, bool):
            value = 1 if value else 0
        if not isinstance(value, int):
            continue
        op_func = _PHASE_FOUR_OPERATORS.get(operator)
        if op_func is not None and op_func(value, threshold):
            return True
    return False


def _evaluate_phase_four_condition(
    condition: str,
    weights: dict[str, object],
) -> bool:
    or_segments = re.split(r"\s+or\s+", condition, flags=re.IGNORECASE)
    if len(or_segments) > 1:
        return any(
            _evaluate_phase_four_condition(segment, weights)
            for segment in or_segments
        )

    and_segments = re.split(r"\s+and\s+", condition, flags=re.IGNORECASE)
    if len(and_segments) > 1:
        return all(
            _evaluate_phase_four_condition(segment, weights)
            for segment in and_segments
        )

    match = _PHASE_FOUR_EXPR_PARSER.fullmatch(condition.strip())
    if not match:
        return False

    key, operator, threshold = match.groups()
    value = weights.get(key)
    if isinstance(value, bool):
        value = 1 if value else 0
    if not isinstance(value, int):
        return False

    op_func = _PHASE_FOUR_OPERATORS.get(operator)
    if op_func is None:
        return False
    return op_func(value, int(threshold))


def engine_weight_keys(engine_type: str) -> list[str]:
    return list(
        ENGINE_REQUIRED_WEIGHTS.get(engine_type, ())
        + OPTIONAL_ENGINE_WEIGHTS.get(engine_type, ())
        + BASE_WEIGHT_KEYS
    )


def all_runtime_weight_keys() -> tuple[str, ...]:
    seen: list[str] = []
    for keys in ENGINE_REQUIRED_WEIGHTS.values():
        for key in keys:
            if key not in seen:
                seen.append(key)
    for keys in OPTIONAL_ENGINE_WEIGHTS.values():
        for key in keys:
            if key not in seen:
                seen.append(key)
    for key in BASE_WEIGHT_KEYS:
        if key not in seen:
            seen.append(key)
    return tuple(seen)
