from __future__ import annotations

from copy import deepcopy
from typing import Any

from .au_college import PRESETS as AU_COLLEGE_PRESETS
from .au_corporate import PRESETS as AU_CORPORATE_PRESETS
from .au_dark import PRESETS as AU_DARK_PRESETS
from .modern_reality_au import PRESETS as AU_MODERN_REALITY_PRESETS
from .relationship_dynamics import PRESETS as RELATIONSHIP_DYNAMICS_PRESETS
from .au_service import PRESETS as SERVICE_AU_PRESETS
from .au_status_power import PRESETS as AU_STATUS_POWER_PRESETS
from .base import _slugify
from .legacy_remaining import NEW_ENGINE_STATE_PRESETS as LEGACY_PRESETS


CATEGORY_PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    "AU_COLLEGE": AU_COLLEGE_PRESETS,
    "AU_MODERN_REALITY": AU_MODERN_REALITY_PRESETS,
    "SERVICE_AU": SERVICE_AU_PRESETS,
    "AU_STATUS_POWER": AU_STATUS_POWER_PRESETS,
    "AU_CORPORATE": AU_CORPORATE_PRESETS,
    "AU_DARK": AU_DARK_PRESETS,
    "RELATIONSHIP_DYNAMICS": RELATIONSHIP_DYNAMICS_PRESETS,
}


BUCKET_SUBGROUP_ENGINE_TYPES: dict[str, dict[str, tuple[str, ...]]] = {
    "MODERN_REALITY": {
        "Everyday": (
            "Amnesia",
            "Classic-Everyday-AU",
            "First-Love",
            "Friends-Lovers",
            "Grumpy-Sunshine",
            "High-School-Sweethearts",
            "Hometown-Anchor",
            "Love-Neighbor",
            "Missing-Years",
            "New-Old-Flame",
            "Renovation-Project",
            "Roommate-Romance",
            "Shared-Utility-Boundary",
            "Shared-Lease",
            "Shared-Wall",
            "Single-Parent-Shield",
            "Small-Town",
            "Beauty-Beast",
            "Cowboy-Ranchers",
            "Plain-Jane",
            "Prank-Paranoia",
            "Ugly-Duckling",
        ),
        "First Meet": (
            "Blank-Page",
            "Blind-Date-Mixup",
            "Critical-Intersect",
            "Cage-Match-Entry",
            "Coffee-Shop-Regular",
            "Cosmic-Anchor",
            "Digital-Seek",
            "Double-Booking",
            "Enclosed-Transit",
            "First-Sight",
            "Lost-Found",
            "Love-Letter-Lunacy",
            "Meet-Crazy",
            "Meet-Cute",
            "Meet-Ugly",
            "Mistaken-Identity",
            "Opaque-Interlude",
            "Opaque-Inversion",
            "Institutional-Rivalry",
            "One-Sided-Cute",
            "Partners-In-Crime",
            "Rebound-Infatuation",
            "Routine-Synchronicity",
            "Secret-Admirer",
            "Screwball-Comedy",
            "Strangers-to-Lovers",
            "Two-Ships-Passing",
            "Wrong-Table",
        ),
        "Travel": (
            "Holiday-Romance",
            "Return-to-Hometown",
            "Road-Trip-Romance",
            "Journey-Romance",
            "Vacation-Countdown",
        ),
        "Social": (
            "Academic-Rivals",
            "Age-Gap",
            "Adult-Strangers-Shift",
            "Algorithmic-Drive",
            "Billionaire-Playboy",
            "Charitable-Proxy",
            "Childhood-Pact",
            "Childhood-Reunion",
            "Climax-Reconnect",
            "Classroom-Proximity",
            "Coach-Athlete",
            "Corporate-Playmaker",
            "Scavenger-Hunt-Bonding",
            "Coachs-Daughter",
            "Cross-Campus",
            "Dorm-Suite",
            "Foundling-Track",
            "Gym-Inversion",
            "Hockey-Forbidden-Sibling",
            "Jock-Tutor",
            "Lineage-Shield",
            "Probation-Alliance",
            "Benchwarmer-Hustle",
            "Rival-Captains",
            "Sports-Football-Rugby",
            "Sports-Baseball",
            "Sports-Hockey",
            "Sports-Basketball",
            "Sports-Soccer",
            "Sports-Tennis-Instructor",
            "Sports-Lacrosse",
            "Sports-Roommate",
            "Sports-Wrestling",
            "Celebrity-Ordinary-Person",
            "Movie-Star-Commoner",
            "Romance-On-Set",
            "Retainer-Date",
            "Rich-Poor",
            "Rockstar-Romance",
            "Shared-Roots",
            "Older-Hero-Younger-Heroine",
            "Older-Heroine-Younger-Hero",
            "Repeating-Intersect",
            "Grumpy-Veteran-Rookie",
            "Crown-Advisor",
            "Century-Void",
            "Cinderella-Circumstance",
            "Starlet-Shield",
            "Ten-Year-Void",
            "Twenty-Five-Benchmark",
            "Heroine-Disguised-as-Man",
            "Heroine-Owes-Hero",
            "Heroine-Pursues-Hero",
            "Heroine-in-Male-Profession",
            "Sexually-Confident-Heroine",
        ),
    },
    "RELATIONSHIPS": {
        "Betrayal": (
            "Accidental-Adultery",
            "Betrayal-Grovel",
            "Bar-Tab-Wager",
            "Broken-Wingman",
            "Calculated-Sabotage",
            "Cynical-Wager",
            "Cynical-Setup",
            "Dare-Repentance",
            "Engineered-Trap",
            "Erased-Barrier",
            "Extorted-Target",
            "Ex-Best-Friend",
            "Ghost-Marriage",
            "Group-Exposure",
            "Infidelity-Melodrama",
            "Lingering-Ex",
            "Loyalty-Breakdown",
            "Martyr-Shield-Crisis",
            "Big-Gesture-Apology",
            "Blackmail",
            "Blackmail-Date",
            "Break-Their-Heart-to-Save-Them",
            "Breakup-Misunderstanding",
            "Extended-Breakup",
            "Jilted-Bride",
            "Overt-Obsession",
            "Partner-Best-Friend",
            "Prank-Date",
            "Proxy-Voice",
            "Revenge-Romance",
            "Relationship-Shattering-Secret",
            "The-Bet",
            "Transactional-Truce",
            "Undercover-Predator",
            "Undercover-Sabotage",
        ),
        "Commitment": (
            "Accidental-Pregnancy",
            "Altar-Flight",
            "Ancestral-Truce",
            "Mail-Order-Bride",
            "Marriage-of-Convenience",
            "Already-Married",
            "Ancestral-Lock",
            "Arranged-Marriage",
            "Fake-Engagement",
            "Infertility-Romance",
            "Legal-Lock-in",
            "Long-Distance-Relationship",
            "Marital-Sham",
            "Preserved-Grief",
            "Runaway-Fiance",
            "Relationship-at-Start",
            "Second-Chance",
            "Single-Parent-Guardian",
            "Vegas-Wedding-Surprise",
            "Widow-Widower",
        ),
        "Situationship": (
            "All-In-Hero",
            "Bully-Romance",
            "Casual-Breach",
            "Fake-Dating",
            "Fake-Relationship",
            "Forbidden-Romance",
            "Forced-Proximity",
            "Friends-Benefits",
            "Hate-to-Love",
            "Hostile-Friction",
            "Himbo-Earnest",
            "Instructional-Proximity",
            "Martyr-Shield-Pact",
            "Martyr-Shield",
            "Matchmaker-Crush",
            "Nostalgia-Anchor",
            "No-Feelings",
            "One-Night-Stand",
            "Opposites-Attract",
            "On-a-Break",
            "Public-Cover-Breach",
            "UST-Slow-Burn",
            "Penpal-Enemy",
            "Bad-Boy-Good-Girl",
            "Chivalric-Code",
            "Contractual-Heartbreak",
            "Earnest-Hustle",
            "Flirt-Coach",
            "Playboy-Rake",
            "Playboy-Virgin",
            "Possessive-Hero",
            "Platonic-Denial",
            "Profile-Conflict",
            "Proxy-Collapse",
            "Pure-Devotion",
            "Puppy-Hero",
            "Performative-Spark",
            "Radiant-Optimizer",
            "Relationship-Coach",
            "Secret-Relationship",
            "Self-Esteem-Issues",
            "Side-Car-Jealousy",
            "Sex-First-Feelings-Later",
            "Socially-Awkward-Hero",
            "Soft-Alpha",
            "Soft-Sanctuary",
            "Surprise-Virgin",
            "Trauma-Slow-Seduction",
            "Tortured-Hero",
            "Unconscious-Bleed",
            "Unrequited-Love",
            "Volatile-Relapse",
        ),
        "Poly": (
            "Best-Friend-Triangle",
            "Harem-Friends",
            "MFF-Triad",
            "MFM-Triad",
            "MMF-Triad",
            "Polyamory-Love",
            "Reverse-Harem",
            "Sovereign-Selection",
            "Menage-a-Trois",
            "Tug-of-War-Triangle",
        ),
        "Family": (
            "Baby-Doorstep",
            "Damaged-Parents",
            "Guardian-Ward",
            "Interfering-Family",
            "Overprotective-Relatives",
            "Romeo-Juliet",
            "Secret-Lovechild",
            "Sibling-Partner",
            "Step-Sibling",
            "Taboo-Betrayal",
        ),
    },
    "WORKPLACE": {
        "Corporate": (
            "Boardroom-Parity",
            "Boardroom-Betrayal",
            "Clinical-Consult",
            "Collateral-Debt",
            "Co-Counsel",
            "Enemies-Boardroom",
            "Workplace-Romance",
            "Mentorship-Romance",
            "Boss-Employee",
            "Cooking-Show",
            "Doctor-Patient",
            "Hostile-Takeover",
            "Lawyer-Client",
            "Legal-Mentorship",
            "Liquidation-Trap",
            "Non-Disclosure-Mask",
            "Office-Benefits",
            "Office-Rivals",
            "Mentorship-Breach",
            "Sandbox-Enemy",
            "Sandbox-Grudge",
            "Silver-Fox-Executive",
            "Teacher-Parent",
            "Teacher-Student",
        ),
        "Services (Domestic)": (
            "Babysitter",
            "Nanny-Romance",
            "Maid-Romance",
            "Pool-Boy",
            "Landscaper-Romance",
        ),
        "Shop": (),
    },
    "DARK": {
        "Supernatural": (
            "Pack-Commander",
            "Sanctuary-Refuge",
            "Instinct-Override",
            "Bloodline-Obligation",
            "Grounding-Anchor",
        ),
        "Underworld": (
            "Band-Brothers",
            "Blood-Truce",
            "Honeymoon-Trap",
            "Mafia-Crime",
            "Mafia-Syndicate",
            "Underworld-High-Stakes",
            "Motorcycle-Club",
            "Street-Biker",
            "Antihero",
            "Asshole-Hero",
            "Bratva-Enforcer",
            "Corrupt-Detective",
            "Cyber-Hacker",
            "Orphan-Pact",
            "Redemption-Romance",
            "Ransom-Bargain",
            "Syndicate-Fixer",
            "Sociopathic-Hero",
            "Tactical-Infatuation",
            "Vigilante-Justice",
            "Deep-Cover-Trap",
            "Mob-Informant",
            "Wiretap-Crisis",
        ),
        "Captivity/Protective": (
            "Amnesia-Haven",
            "Back-From-Dead",
            "Bodyguard-Romance",
            "Bodyguard-Captivity",
            "Bondage-Restraint",
            "Bodyguard-Protection",
            "Caretaker-Infiltration",
            "Castaway-Survival",
            "Captive-Captor",
            "Caretaker-Recovery",
            "Cartel-Isolation",
            "Collateral-Bride",
            "Guilt-Ridden-Anchor",
            "Indentured-Servitude",
            "Instant-Castaway",
            "Inverted-Captivity",
            "Kidnapping-Romance",
            "Luxury-Confinement",
            "Navy-SEALs",
            "On-the-Run",
            "One-Night-of-Danger",
            "Flight-Crisis",
            "Preserved-Identity",
            "Rescue-Romance",
            "Stockholm-Syndrome",
            "Suburban-Mask",
            "Survival-Romance",
            "Underworld-Medic",
            "Witness-Protection",
        ),
        "BDSM": (
            "BDSM-Exchange",
            "Brat-Taming",
            "CNC-Exchange",
            "Escort-Transaction",
            "Kinbaku-Restraint",
            "Primal-Chase",
            "Sex-Club",
            "Spanking-Discipline",
            "Total-Power-Exchange",
            "Virgin-Auction",
        ),
        "NSFW/Explicit": (
            "DDLG-Exchange",
            "Omegaverse-Supernatural",
            "Payment-Debt",
            "Stripper-Performance",
        ),
    },
}


NEW_ENGINE_STATE_PRESETS: dict[str, dict[str, Any]] = dict(LEGACY_PRESETS)
for preset_group in CATEGORY_PRESETS.values():
    NEW_ENGINE_STATE_PRESETS.update(preset_group)


BUCKET_SUBGROUP_AVAILABLE_PRESETS: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
ENGINE_BUCKET_INDEX: dict[str, tuple[str, str]] = {}

for bucket_name, subgroup_map in BUCKET_SUBGROUP_ENGINE_TYPES.items():
    BUCKET_SUBGROUP_AVAILABLE_PRESETS[bucket_name] = {}
    for subgroup_name, engine_types in subgroup_map.items():
        subgroup_presets = {
            engine_type: NEW_ENGINE_STATE_PRESETS[engine_type]
            for engine_type in engine_types
            if engine_type in NEW_ENGINE_STATE_PRESETS
        }
        BUCKET_SUBGROUP_AVAILABLE_PRESETS[bucket_name][subgroup_name] = subgroup_presets
        for engine_type in engine_types:
            ENGINE_BUCKET_INDEX[engine_type] = (bucket_name, subgroup_name)


BUCKET_AVAILABLE_PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    bucket_name: {
        engine_type: preset
        for subgroup_presets in subgroup_map.values()
        for engine_type, preset in subgroup_presets.items()
    }
    for bucket_name, subgroup_map in BUCKET_SUBGROUP_AVAILABLE_PRESETS.items()
}

SUPERSEDED_SAFE_EQUIVALENTS: dict[str, str] = {
    "Boss-Employee": "Boardroom-Parity",
    "Doctor-Patient": "Clinical-Consult",
    "Lawyer-Client": "Co-Counsel",
    "Step-Sibling": "Shared-Utility-Boundary",
    "Teacher-Student": "Academic-Rivals",
}


NO_PRESET_YET_ENGINE_TYPES: tuple[str, ...] = tuple(
    sorted(
        engine_type
        for engine_type in ENGINE_BUCKET_INDEX
        if engine_type not in NEW_ENGINE_STATE_PRESETS
        and engine_type not in SUPERSEDED_SAFE_EQUIVALENTS
    )
)


def build_engine_state_card(
    engine_type: str,
    *,
    card_id: str | None = None,
    name: str | None = None,
    current_phase: int = 1,
) -> dict[str, Any]:
    if engine_type not in NEW_ENGINE_STATE_PRESETS:
        if engine_type in SUPERSEDED_SAFE_EQUIVALENTS:
            replacement = SUPERSEDED_SAFE_EQUIVALENTS[engine_type]
            raise ValueError(
                f"Engine '{engine_type}' is intentionally superseded by safe equivalent '{replacement}' and is not scaffolded directly."
            )
        if engine_type in NO_PRESET_YET_ENGINE_TYPES:
            raise ValueError(
                f"Engine '{engine_type}' is bucketed in the taxonomy but has no preset scaffold yet."
            )
        raise KeyError(engine_type)
    preset = NEW_ENGINE_STATE_PRESETS[engine_type]
    return {
        "card_id": card_id or f"{_slugify(engine_type)}_asset",
        "metadata": {
            "name": name or preset["default_name"],
            "archetype": preset["archetype"],
            "engine_type": engine_type,
            "current_phase": current_phase,
        },
        "trope_engine_weights": deepcopy(preset["weights"]),
        "origin_context": deepcopy(preset["origin_context"]),
        "dialogue_nodes": deepcopy(preset["dialogue_nodes"]),
    }


def has_engine_state_preset(engine_type: str) -> bool:
    return engine_type in NEW_ENGINE_STATE_PRESETS


def bucket_for_engine(engine_type: str) -> tuple[str, str] | None:
    return ENGINE_BUCKET_INDEX.get(engine_type)


def legacy_origin_block_name(engine_type: str) -> str:
    return f"{_slugify(engine_type)}_origin"
