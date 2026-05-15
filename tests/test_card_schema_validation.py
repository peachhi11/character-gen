from __future__ import annotations

import json
from pathlib import Path
import unittest

from character_app.card_schema_validation import CharacterCardValidator
from character_app.engine_state_card_presets import build_engine_state_card
from character_app.trope_engine_catalog import phase_four_activation_condition


ROOT_DIR = Path(__file__).resolve().parents[1]


class CharacterCardSchemaValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = CharacterCardValidator()
        self.schema_path = (
            ROOT_DIR
            / "character_app"
            / "schemas"
            / "trope_engine_character_card.schema.json"
        )

    def make_payload(self, engine_type: str) -> dict:
        payload = {
            "card_id": "char_test",
            "metadata": {
                "name": "Test",
                "archetype": "The Test Archetype",
                "engine_type": engine_type,
                "current_phase": 1,
            },
            "trope_engine_weights": {
                "lie_active": False,
                "lie_count": 0,
                "angst_meter": 1,
            },
            "origin_context": {
                "environment_type": "Academic",
                "incident_summary": "A collision over the last remaining library book.",
                "spark_token": "Coffee-stained notes.",
                "unbreakable_tether": "Assigned co-authors.",
            },
            "dialogue_nodes": {
                "phase_1_baseline": {
                    "greeting": "Hello.",
                    "body_language_descriptor": "They keep their hands folded on the desk.",
                },
                "phase_4_breaking_point": {
                    "activation_condition": "romantic_tension >= 4",
                    "dialogue_payload": "Look at me.",
                    "action_prompt": "They step into your space.",
                },
                "phase_5_hangover_crisis": {
                    "if_player_lied": "Let's forget it.",
                    "if_player_honest": "Even now?",
                },
            },
        }
        if engine_type == "Meet-Cute":
            payload["trope_engine_weights"].update(
                {"platonic_trust": 3, "romantic_awareness": 1, "fear_of_loss": 3}
            )
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "romantic_awareness >= 4"
        elif engine_type == "Meet-Ugly":
            payload["trope_engine_weights"].update(
                {"rivalry_heat": 4, "repressed_desire": 1}
            )
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "repressed_desire >= 4"
        elif engine_type == "Meet-Crazy":
            payload["trope_engine_weights"].update(
                {
                    "chaotic_chemistry": 3,
                    "adrenaline_level": 4,
                    "emotional_depth": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Public spectacle"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "chaotic_chemistry >= 4"
        elif engine_type == "Forced-Proximity":
            payload["trope_engine_weights"].update(
                {
                    "confinement_stress": 5,
                    "hostile_friction_heat": 4,
                    "proximity_awareness_acceleration": 2,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Locked room"
        elif engine_type == "Strangers-to-Lovers":
            payload["trope_engine_weights"].update(
                {
                    "social_distance": 4,
                    "observational_focus": 2,
                    "vulnerability_thaw": 0,
                }
            )
            payload["origin_context"]["environment_type"] = "Crowded transit station"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "observational_focus >= 4"
        elif engine_type == "Second-Chance":
            payload["trope_engine_weights"].update(
                {
                    "past_breakup_baggage": 4,
                    "protective_pride_shield": 4,
                    "residual_heartbreak": 2,
                    "lie_active": True,
                    "lie_count": 1,
                    "angst_meter": 3,
                }
            )
            payload["origin_context"]["environment_type"] = "Room still charged with too much shared history"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "residual_heartbreak <= 1 and protective_pride_shield <= 1"
        elif engine_type == "Forbidden-Romance":
            payload["trope_engine_weights"].update(
                {
                    "systemic_restraint": 4,
                    "stolen_proximity": 2,
                    "fear_of_exposure": 4,
                    "distance_locked": True,
                    "angst_meter": 3,
                }
            )
            payload["origin_context"]["environment_type"] = "After-hours office with one locked door between desire and fallout"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "stolen_proximity >= 4"
        elif engine_type == "Fake-Dating":
            payload["trope_engine_weights"].update(
                {
                    "performative_closeness": 4,
                    "private_confusion": 2,
                    "boundary_panic": 2,
                    "angst_meter": 1,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Doorway just after the audience and excuses finally clear out"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "private_confusion >= 4"
        elif engine_type == "Best-Friend-Triangle":
            payload["trope_engine_weights"].update(
                {
                    "shared_platonic_trust": 4,
                    "internal_jealousy": 1,
                    "attraction_imbalance": 2,
                    "angst_meter": 2,
                }
            )
            payload["origin_context"]["environment_type"] = "Shared Hometown Commons Lounge"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "internal_jealousy >= 4"
        elif engine_type == "Partner-Best-Friend":
            payload["trope_engine_weights"].update(
                {
                    "loyalty_guilt": 4,
                    "forbidden_proximity": 1,
                    "repressed_fixation": 2,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Mutual friend's engagement party"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "repressed_fixation >= 4"
        elif engine_type == "Tug-of-War-Triangle":
            payload["trope_engine_weights"].update(
                {
                    "possessive_heat": 4,
                    "rivalry_panic": 3,
                    "boundary_assertion": 2,
                    "angst_meter": 3,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Crowded event floor the moment a rival steps into your orbit"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "rivalry_panic >= 4"
        elif engine_type == "Accidental-Pregnancy":
            payload["trope_engine_weights"].update(
                {
                    "domestic_panic": 4,
                    "forced_co_dependence": 4,
                    "protective_instinct": 2,
                    "angst_meter": 3,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Quiet room where obligation just started feeling dangerously personal"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "forced_co_dependence >= 5"
        elif engine_type == "Secret-Lovechild":
            payload["trope_engine_weights"].update(
                {
                    "historical_hurt_index": 4,
                    "parental_shield_drive": 4,
                    "exposure_panic_heat": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Living room after years of silence stopped being sustainable"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "parental_shield_drive >= 5"
        elif engine_type == "One-Night-Stand":
            payload["trope_engine_weights"].update(
                {
                    "physical_hyper_awareness": 5,
                    "social_panic_index": 4,
                    "denial_mask_integrity": 3,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Boardroom doorway after a one-night stand was supposed to stay buried"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "physical_hyper_awareness >= 5"
        elif engine_type == "Matchmaker-Crush":
            payload["trope_engine_weights"].update(
                {
                    "performative_guidance": 5,
                    "proxy_resentment": 1,
                    "physical_hyper_awareness": 1,
                    "angst_meter": 1,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Apartment kitchen turned into an impromptu dating strategy station"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "physical_hyper_awareness >= 4"
        elif engine_type == "Relationship-Coach":
            payload["trope_engine_weights"].update(
                {
                    "instructional_intimacy": 4,
                    "transactional_boundary": 4,
                    "private_obsession_heat": 1,
                    "angst_meter": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Rooftop bar balcony used as a live flirting classroom"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "private_obsession_heat >= 4"
        elif engine_type == "Arranged-Marriage":
            payload["trope_engine_weights"].update(
                {
                    "contractual_lock": 5,
                    "clinical_politeness": 4,
                    "undercurrent_fixation": 1,
                    "angst_meter": 3,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Penthouse divided by contract and freezing politeness"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "undercurrent_fixation >= 4"
        elif engine_type == "Childhood-Pact":
            payload["trope_engine_weights"].update(
                {
                    "nostalgia_anchor": 5,
                    "pact_relevance_panic": 4,
                    "fear_of_rejection": 3,
                    "angst_meter": 1,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Car hood under a quiet streetlight at the midnight deadline"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "pact_relevance_panic >= 4"
        elif engine_type == "Jilted-Bride":
            payload["trope_engine_weights"].update(
                {
                    "public_humiliation": 5,
                    "unresolved_heartbreak": 4,
                    "defensive_pride": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Chapel reception hall after the music has long since died"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "unresolved_heartbreak >= 5"
        elif engine_type == "Runaway-Fiance":
            payload["trope_engine_weights"].update(
                {
                    "commitment_panic": 5,
                    "abandonment_guilt": 4,
                    "lingering_fixation_heat": 2,
                    "angst_meter": 3,
                }
            )
            payload["origin_context"]["environment_type"] = "Quiet refuge where running finally started to feel optional"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "lingering_fixation_heat >= 4"
        elif engine_type == "Fake-Relationship":
            payload["trope_engine_weights"].update(
                {
                    "performative_closeness": 4,
                    "private_confusion": 3,
                    "boundary_panic_heat": 2,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Shared room built around a long-term cover story nobody can exit casually anymore"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "private_confusion >= 4"
        elif engine_type == "Secret-Relationship":
            payload["trope_engine_weights"].update(
                {
                    "systemic_restraint": 4,
                    "stolen_proximity": 2,
                    "fear_of_exposure": 4,
                    "angst_meter": 3,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Locked office after midnight"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "stolen_proximity >= 4"
        elif engine_type == "Prank-Date":
            payload["trope_engine_weights"].update(
                {
                    "malicious_intent": 4,
                    "shame_collapse": 1,
                    "genuine_fixation": 1,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Diner booth under fluorescent lights after the joke stopped feeling funny"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "shame_collapse >= 4"
        elif engine_type == "Bully-Romance":
            payload["trope_engine_weights"].update(
                {
                    "overt_antagonism": 4,
                    "buried_fixation": 2,
                    "power_dominance": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Locker-lined hallway where hostility has always been the easiest language to reach for first"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "buried_fixation >= 4"
        elif engine_type == "Tortured-Hero":
            payload["trope_engine_weights"].update(
                {
                    "internal_trauma": 5,
                    "emotional_detachment": 4,
                    "rescue_resistance": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Safehouse infirmary"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "emotional_detachment <= 1"
        elif engine_type == "Hate-to-Love":
            payload["trope_engine_weights"].update(
                {
                    "hostile_friction": 4,
                    "physical_attraction": 1,
                    "repressed_heat": 2,
                    "angst_meter": 3,
                }
            )
            payload["origin_context"]["environment_type"] = "Boardroom argument at midnight"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "repressed_heat >= 4"
        elif engine_type == "Revenge-Romance":
            payload["trope_engine_weights"].update(
                {
                    "manipulation_drive": 5,
                    "network_infiltration": 4,
                    "loyalty_sabotage_heat": 1,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Private dinner room overlooking the target family's corporate floor"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "loyalty_sabotage_heat >= 4"
        elif engine_type == "Blackmail-Date":
            payload["trope_engine_weights"].update(
                {
                    "coercive_leverage": 4,
                    "hostile_compliance": 3,
                    "power_inversion": 1,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Dimly lit VIP restaurant alcove"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "power_inversion >= 4"
        elif engine_type == "The-Bet":
            payload["trope_engine_weights"].update(
                {
                    "cynical_wager_leverage": 4,
                    "peer_validation_drive": 3,
                    "guilt_conversion_heat": 0,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Loud high-density college campus bar"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "guilt_conversion_heat >= 4"
        elif engine_type == "Mafia-Crime":
            payload["trope_engine_weights"].update(
                {
                    "underworld_dominance": 5,
                    "lethal_risk_factor": 4,
                    "protective_obsession": 2,
                    "angst_meter": 4,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Private club war room"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "protective_obsession >= 4"
        elif engine_type == "Captive-Captor":
            payload["trope_engine_weights"].update(
                {
                    "confinement_stress": 5,
                    "power_asymmetry": 5,
                    "trauma_bonding": 1,
                    "angst_meter": 4,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Secluded mountain safehouse vault"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "trauma_bonding >= 4"
        elif engine_type == "Escort-Transaction":
            payload["trope_engine_weights"].update(
                {
                    "transactional_boundary": 5,
                    "performative_intimacy": 4,
                    "private_numbness": 2,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Hotel suite after hours"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "private_numbness <= 1"
        elif engine_type == "Sex-Club":
            payload["trope_engine_weights"].update(
                {
                    "sensory_exposure": 4,
                    "performative_heat": 3,
                    "exclusive_fixation": 1,
                    "angst_meter": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Subterranean velvet lounge"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "exclusive_fixation >= 4"
        elif engine_type == "Virgin-Auction":
            payload["trope_engine_weights"].update(
                {
                    "financial_leverage": 5,
                    "ownership_heat": 4,
                    "protective_safeguard": 1,
                    "angst_meter": 4,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "High-society underworld auction gala"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "protective_safeguard >= 4"
        elif engine_type == "BDSM-Exchange":
            payload["trope_engine_weights"].update(
                {
                    "power_exchange_heat": 4,
                    "consent_restraint": 3,
                    "aftercare_safety": 2,
                    "angst_meter": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Private dungeon suite"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "power_exchange_heat >= 4"
        elif engine_type == "Rescue-Romance":
            payload["trope_engine_weights"].update(
                {
                    "protector_drive": 5,
                    "trauma_thaw": 1,
                    "vulnerability_spike": 2,
                    "angst_meter": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Secured remote mountain cabin"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "trauma_thaw >= 4"
        elif engine_type == "Step-Sibling":
            payload["trope_engine_weights"].update(
                {
                    "domestic_lock": 4,
                    "family_friction": 4,
                    "repressed_fixation": 2,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Upstairs hallway outside a bedroom"
            payload["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ] = "repressed_fixation >= 4"
        elif engine_type == "Teacher-Parent":
            payload["trope_engine_weights"].update(
                {
                    "professional_boundary": 4,
                    "parental_protective_drive": 3,
                    "situational_awkwardness": 2,
                    "angst_meter": 2,
                }
            )
            payload["origin_context"]["environment_type"] = "Parent-teacher conference room"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "professional_boundary <= 1"
        elif engine_type == "Academic-Rivals":
            payload["trope_engine_weights"].update(
                {
                    "academic_risk_factor": 5,
                    "hidden_proximity": 4,
                    "evaluation_panic": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Seminar room after hours"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "hidden_proximity >= 5"
        elif engine_type == "Teacher-Student":
            payload["trope_engine_weights"].update(
                {
                    "academic_risk_factor": 5,
                    "hidden_proximity": 4,
                    "evaluation_panic": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Lecture hall after hours"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "hidden_proximity >= 5"
        elif engine_type == "Boardroom-Parity":
            payload["trope_engine_weights"].update(
                {
                    "promotion_rivalry_heat": 4,
                    "favoritism_paranoia": 4,
                    "private_fixation": 2,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Executive office suite after a late board review"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "private_fixation >= 4"
        elif engine_type == "Boss-Employee":
            payload["trope_engine_weights"].update(
                {
                    "corporate_asymmetry": 5,
                    "favoritism_paranoia": 4,
                    "private_fixation": 2,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Executive elevator"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "private_fixation >= 4"
        elif engine_type == "Age-Gap":
            payload["trope_engine_weights"].update(
                {
                    "generational_variance": 4,
                    "protective_seniority": 4,
                    "social_disapproval_heat": 3,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Townhouse doorway at midnight"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "protective_seniority >= 5"
        elif engine_type == "Doctor-Patient":
            payload["trope_engine_weights"].update(
                {
                    "ethical_restraint": 5,
                    "clinical_objectivity": 4,
                    "vulnerability_spike": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Private examination room"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "clinical_objectivity <= 1"
        elif engine_type == "Clinical-Consult":
            payload["trope_engine_weights"].update(
                {
                    "ethical_restraint": 5,
                    "clinical_objectivity": 4,
                    "vulnerability_spike": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Private consultation room off a trauma ward"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "clinical_objectivity <= 1"
        elif engine_type == "Lawyer-Client":
            payload["trope_engine_weights"].update(
                {
                    "legal_stakes_heat": 5,
                    "confidential_proximity": 4,
                    "conflict_of_interest": 3,
                    "angst_meter": 4,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Late-night deposition office"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "confidential_proximity >= 5"
        elif engine_type == "Co-Counsel":
            payload["trope_engine_weights"].update(
                {
                    "legal_stakes_heat": 5,
                    "confidential_proximity": 4,
                    "conflict_of_interest": 3,
                    "angst_meter": 4,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Privilege-walled war room behind closed blinds"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "confidential_proximity >= 5"
        elif engine_type == "Billionaire-Playboy":
            payload["trope_engine_weights"].update(
                {
                    "capital_leverage": 5,
                    "media_scrutiny_heat": 4,
                    "exclusive_fixation": 1,
                    "angst_meter": 1,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Town car behind a gala"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "exclusive_fixation >= 4"
        elif engine_type == "Office-Benefits":
            payload["trope_engine_weights"].update(
                {
                    "transactional_casualty": 4,
                    "cubicle_proximity": 4,
                    "private_fixation": 1,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Breakroom and copy room loop"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "private_fixation >= 4"
        elif engine_type == "Office-Rivals":
            payload["trope_engine_weights"].update(
                {
                    "promotion_rivalry_heat": 4,
                    "hostile_friction": 4,
                    "competence_respect": 2,
                    "angst_meter": 3,
                }
            )
            payload["origin_context"]["environment_type"] = "Sales floor at midnight"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "competence_respect >= 4"
        elif engine_type == "Cooking-Show":
            payload["trope_engine_weights"].update(
                {
                    "sensory_exposure": 4,
                    "media_performance_heat": 3,
                    "timer_stress_boundary": 3,
                    "angst_meter": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Studio kitchen station"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "sensory_exposure >= 4"
        elif engine_type == "Pack-Commander":
            payload["trope_engine_weights"].update(
                {
                    "hierarchy_dominance": 5,
                    "pack_protective_drive": 4,
                    "territorial_panic": 1,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Council chamber after a rival challenge"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "territorial_panic >= 4"
        elif engine_type == "Sanctuary-Refuge":
            payload["trope_engine_weights"].update(
                {
                    "independent_resistance_mask": 5,
                    "sanctuary_drive": 3,
                    "exposure_panic": 2,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Hidden safehouse lounge"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "sanctuary_drive >= 4 and exposure_panic >= 4"
        elif engine_type == "Instinct-Override":
            payload["trope_engine_weights"].update(
                {
                    "instinct_pressure": 5,
                    "accelerated_proximity": 5,
                    "rational_resistance": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Secure operations room after a breach alert"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "rational_resistance <= 1"
        elif engine_type == "Bloodline-Obligation":
            payload["trope_engine_weights"].update(
                {
                    "bloodline_obligation": 5,
                    "council_honor_code": 4,
                    "private_emotional_capture": 1,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Ancestral manor archive"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "private_emotional_capture >= 4"
        elif engine_type == "Grounding-Anchor":
            payload["trope_engine_weights"].update(
                {
                    "grounding_reliability": 5,
                    "emotional_anchoring": 4,
                    "crisis_mitigation": 3,
                    "angst_meter": 1,
                    "lie_active": False,
                    "lie_count": 0,
                    "distance_locked": False,
                }
            )
            payload["origin_context"]["environment_type"] = "Quiet apartment kitchen after a panic spiral"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "grounding_reliability >= 5 and crisis_mitigation >= 4"
        elif engine_type == "Band-Brothers":
            payload["trope_engine_weights"].update(
                {
                    "fraternal_loyalty_shield": 5,
                    "tactical_proximity": 4,
                    "protective_obsession": 2,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Forward operating lineup"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "protective_obsession >= 4"
        elif engine_type == "Harem-Friends":
            payload["trope_engine_weights"].update(
                {
                    "group_status_quo_friction": 4,
                    "proxy_competitive_panic": 3,
                    "jealousy_heat": 1,
                    "angst_meter": 2,
                }
            )
            payload["origin_context"]["environment_type"] = "Loud group circle where fake peace is starting to crack"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "jealousy_heat >= 4"
        elif engine_type == "Polyamory-Love":
            payload["trope_engine_weights"].update(
                {
                    "multi_party_equilibrium": 4,
                    "boundary_negotiation": 4,
                    "psychological_safety": 2,
                    "angst_meter": 1,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Circular table set for a conversation that was supposed to stay calm"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "boundary_negotiation <= 1"
        elif engine_type == "MMF-Triad":
            payload["trope_engine_weights"].update(
                {
                    "alpha_friction_heat": 4,
                    "shared_possessive_heat": 4,
                    "synchronized_obsession": 1,
                    "angst_meter": 3,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Locked private suite with both exits already watched"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "synchronized_obsession >= 4"
        elif engine_type == "MFM-Triad":
            payload["trope_engine_weights"].update(
                {
                    "parallel_attraction": 4,
                    "truce_buffer_comfort": 4,
                    "protective_safeguard": 2,
                    "angst_meter": 2,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Leather sectional arranged to feel intentionally safe"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "parallel_attraction >= 4"
        elif engine_type == "MFF-Triad":
            payload["trope_engine_weights"].update(
                {
                    "domestic_rebalancing": 4,
                    "dual_female_friction": 3,
                    "emotional_equilibrium": 2,
                    "angst_meter": 2,
                    "distance_locked": True,
                }
            )
            payload["origin_context"]["environment_type"] = "Master bedroom double doors closed against the rest of the house"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "domestic_rebalancing >= 4"
        elif engine_type == "Sovereign-Selection":
            payload["trope_engine_weights"].update(
                {
                    "suitor_density_load": 4,
                    "selection_stress_index": 4,
                    "horizontal_ranking_score": 2,
                    "angst_meter": 3,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Mantelpiece and sitting room built for a courtly performance nobody can sustain cleanly anymore"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "selection_stress_index >= 4"
        elif engine_type == "No-Feelings":
            payload["trope_engine_weights"].update(
                {
                    "emotional_detachment": 5,
                    "physical_hyper_awareness": 4,
                    "boundary_panic_heat": 2,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Apartment door at sunrise"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "boundary_panic_heat >= 4"
        elif engine_type == "Friends-Benefits":
            payload["trope_engine_weights"].update(
                {
                    "platonic_baseline_trust": 4,
                    "contractual_intimacy": 4,
                    "private_romantic_fixation": 1,
                    "angst_meter": 2,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Shared couch after midnight"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "private_romantic_fixation >= 4"
        elif engine_type == "Friends-Lovers":
            payload["trope_engine_weights"].update(
                {
                    "historical_security": 5,
                    "fear_of_relationship_loss": 4,
                    "physical_awareness_shift": 1,
                    "angst_meter": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Best-friend living room"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = "physical_awareness_shift >= 4"
        elif engine_type == "Accidental-Adultery":
            payload["trope_engine_weights"].update(
                {
                    "moral_crisis_heat": 5,
                    "hidden_marital_baggage": 4,
                    "guilt_conversion_index": 3,
                    "angst_meter": 4,
                    "lie_active": True,
                    "lie_count": 1,
                }
            )
            payload["origin_context"]["environment_type"] = "Dimly lit after-hours office suite"
            payload["dialogue_nodes"]["phase_4_breaking_point"]["activation_condition"] = (
                "guilt_conversion_index >= 4 or moral_crisis_heat == 5 and guilt_conversion_index >= 3"
            )
        else:
            try:
                return build_engine_state_card(
                    engine_type,
                    card_id="char_test",
                    name="Test",
                    current_phase=1,
                )
            except KeyError as exc:
                raise ValueError(engine_type) from exc
        return payload

    def test_rejects_invalid_engine_type(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        payload["metadata"]["engine_type"] = "Enemies-to-Lovers"
        result = self.validator.validate_card_json(payload)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("Invalid engine type" in error for error in result.errors))

    def test_canonical_schema_artifact_is_valid_json(self) -> None:
        self.assertTrue(self.schema_path.exists())
        schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["title"], "TropeEngineCharacterCard")
        self.assertIn("origin_context", schema["required"])

    def test_backfills_legacy_base_relationship_into_engine_type(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        del payload["metadata"]["engine_type"]
        payload["metadata"]["base_relationship"] = "Meet-Ugly"
        result = self.validator.validate_card_json(payload)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(
            result.normalized_card["metadata"]["engine_type"], "Meet-Ugly"
        )
        self.assertTrue(
            any("Backfilled 'metadata.engine_type'" in warning for warning in result.warnings)
        )

    def test_clamps_out_of_bounds_weight_values(self) -> None:
        payload = self.make_payload("Meet-Crazy")
        payload["trope_engine_weights"]["chaotic_chemistry"] = 9
        payload["trope_engine_weights"]["adrenaline_level"] = -2

        result = self.validator.validate_card_json(payload)

        self.assertEqual(result.status, "PASS")
        self.assertEqual(
            result.normalized_card["trope_engine_weights"]["chaotic_chemistry"], 5
        )
        self.assertEqual(
            result.normalized_card["trope_engine_weights"]["adrenaline_level"], 0
        )
        self.assertTrue(
            any("Clamped out-of-bounds weight 'chaotic_chemistry'" in w for w in result.warnings)
        )

    def test_rejects_missing_engine_specific_weight(self) -> None:
        payload = self.make_payload("Forced-Proximity")
        del payload["trope_engine_weights"]["proximity_awareness_acceleration"]
        result = self.validator.validate_card_json(payload)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(
            any(
                "Missing required weight 'proximity_awareness_acceleration'" in error
                for error in result.errors
            )
        )

    def test_backfills_legacy_forced_proximity_weights(self) -> None:
        payload = self.make_payload("Forced-Proximity")
        del payload["trope_engine_weights"]["hostile_friction_heat"]
        del payload["trope_engine_weights"]["proximity_awareness_acceleration"]
        payload["trope_engine_weights"]["proximity_heat"] = 3

        result = self.validator.validate_card_json(payload)

        self.assertEqual(result.status, "PASS")
        self.assertEqual(
            result.normalized_card["trope_engine_weights"][
                "proximity_awareness_acceleration"
            ],
            3,
        )
        self.assertEqual(
            result.normalized_card["trope_engine_weights"]["hostile_friction_heat"],
            4,
        )

    def test_accepts_registered_engine_weights(self) -> None:
        for engine_type in sorted(self.validator.valid_engines):
            with self.subTest(engine_type=engine_type):
                result = self.validator.validate_card_json(self.make_payload(engine_type))
                self.assertEqual(result.status, "PASS")

    def test_rejects_second_chance_without_active_barrier_at_max_hurt(self) -> None:
        payload = self.make_payload("Second-Chance")
        payload["trope_engine_weights"]["past_breakup_baggage"] = 5
        payload["trope_engine_weights"]["protective_pride_shield"] = 0

        result = self.validator.validate_card_json(payload)

        self.assertEqual(result.status, "FAIL")
        self.assertTrue(
            any("Second-Chance" in error for error in result.errors)
        )

    def test_normalizes_blank_activation_condition(self) -> None:
        payload = self.make_payload("Meet-Cute")
        payload["dialogue_nodes"]["phase_4_breaking_point"][
            "activation_condition"
        ] = "   "
        result = self.validator.validate_card_json(payload)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(
            result.normalized_card["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ],
            phase_four_activation_condition("Meet-Cute"),
        )
        self.assertTrue(
            any("Normalized activation_condition" in warning for warning in result.warnings)
        )

    def test_rejects_lie_active_without_lie_count(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        payload["trope_engine_weights"]["lie_count"] = 0
        payload["trope_engine_weights"]["lie_active"] = True
        result = self.validator.validate_card_json(json.dumps(payload))
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("Logical Paradox" in error for error in result.errors))

    def test_rejects_soft_lock_initialization(self) -> None:
        payload = self.make_payload("Meet-Cute")
        payload["trope_engine_weights"]["platonic_trust"] = 5
        payload["trope_engine_weights"]["angst_meter"] = 5
        result = self.validator.validate_card_json(payload)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("Soft-lock Risk" in error for error in result.errors))

    def test_rejects_lie_active_without_rivalry_heat(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        payload["trope_engine_weights"]["rivalry_heat"] = 0
        payload["trope_engine_weights"]["lie_count"] = 1
        payload["trope_engine_weights"]["lie_active"] = True
        result = self.validator.validate_card_json(payload)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("Logical Conflict" in error for error in result.errors))

    def test_backfills_origin_context_from_legacy_origin_block(self) -> None:
        payload = self.make_payload("Meet-Crazy")
        del payload["origin_context"]
        payload["meet_crazy_origin"] = {
            "type": "Public spectacle",
            "spectacle": "A wedding escape.",
            "token": "Wedding cake frosting.",
            "lock": "One shared getaway car.",
        }
        result = self.validator.validate_card_json(payload)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(
            result.normalized_card["origin_context"]["incident_summary"],
            "A wedding escape.",
        )
        self.assertEqual(
            result.normalized_card["origin_context"]["unbreakable_tether"],
            "One shared getaway car.",
        )
        self.assertTrue(
            any("Backfilled canonical 'origin_context'" in warning for warning in result.warnings)
        )

    def test_backfills_canonical_dialogue_keys_from_legacy_aliases(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        baseline = payload["dialogue_nodes"]["phase_1_baseline"]
        breaking = payload["dialogue_nodes"]["phase_4_breaking_point"]
        del baseline["body_language_descriptor"]
        baseline["body_language"] = "They refuse to look away."
        del breaking["activation_condition"]
        del breaking["dialogue_payload"]
        breaking["trigger_condition"] = "romantic_tension >= 4"
        breaking["dialogue"] = "You have my attention."

        result = self.validator.validate_card_json(payload)

        self.assertEqual(result.status, "PASS")
        self.assertEqual(
            result.normalized_card["dialogue_nodes"]["phase_1_baseline"][
                "body_language_descriptor"
            ],
            "They refuse to look away.",
        )
        self.assertEqual(
            result.normalized_card["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ],
            phase_four_activation_condition("Meet-Ugly"),
        )
        self.assertEqual(
            result.normalized_card["dialogue_nodes"]["phase_4_breaking_point"][
                "dialogue_payload"
            ],
            "You have my attention.",
        )

    def test_catalog_overrides_mismatched_phase_four_trigger_string(self) -> None:
        payload = self.make_payload("Meet-Ugly")
        payload["dialogue_nodes"]["phase_4_breaking_point"][
            "activation_condition"
        ] = "totally_wrong_metric >= 99"

        result = self.validator.validate_card_json(payload)

        self.assertEqual(result.status, "PASS")
        self.assertEqual(
            result.normalized_card["dialogue_nodes"]["phase_4_breaking_point"][
                "activation_condition"
            ],
            phase_four_activation_condition("Meet-Ugly"),
        )
        self.assertTrue(
            any("Normalized activation_condition" in warning for warning in result.warnings)
        )


if __name__ == "__main__":
    unittest.main()
