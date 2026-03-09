"""
optimizer/constraints.py — Pokemon pool filtering and constraint validation.

Translates an OptimizeRequest into a filtered list of eligible Pokemon,
and validates that any proposed team satisfies all hard constraints.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from optimizer.models import (
    AvailabilityMode,
    AvailabilityTier,
    OptimizeRequest,
    Pokemon,
    PokemonType,
)

_POKEMON_DATA_PATH = Path(__file__).parent.parent / "data" / "pokemon.json"

# Maps generation numbers to their canonical game slugs
GEN_TO_GAMES: dict[int, list[str]] = {
    1: ["red", "blue", "yellow"],
    2: ["gold", "silver", "crystal"],
    3: ["ruby", "sapphire", "emerald", "firered", "leafgreen"],
    4: ["diamond", "pearl", "platinum", "heartgold", "soulsilver"],
    5: ["black", "white", "black2", "white2"],
    6: ["x", "y", "omegaruby", "alphasapphire"],
    7: ["sun", "moon", "ultrasun", "ultramoon", "letsgopikachu", "letsgoeevee"],
    8: ["sword", "shield", "brilliantdiamond", "shiningpearl", "legendsarceus"],
    9: ["scarlet", "violet"],
}

# Paired version games — if both selected, version exclusives become available via trade
VERSION_PAIRS: set[frozenset[str]] = {
    frozenset({"red", "blue"}),
    frozenset({"gold", "silver"}),
    frozenset({"ruby", "sapphire"}),
    frozenset({"firered", "leafgreen"}),
    frozenset({"diamond", "pearl"}),
    frozenset({"heartgold", "soulsilver"}),
    frozenset({"black", "white"}),
    frozenset({"black2", "white2"}),
    frozenset({"x", "y"}),
    frozenset({"omegaruby", "alphasapphire"}),
    frozenset({"sun", "moon"}),
    frozenset({"ultrasun", "ultramoon"}),
    frozenset({"letsgopikachu", "letsgoeevee"}),
    frozenset({"sword", "shield"}),
    frozenset({"brilliantdiamond", "shiningpearl"}),
    frozenset({"scarlet", "violet"}),
}


@lru_cache(maxsize=1)
def load_all_pokemon() -> list[Pokemon]:
    """Load and parse all Pokemon from the static dataset. Cached after first call."""
    if not _POKEMON_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Pokemon dataset not found at {_POKEMON_DATA_PATH}. "
            "Run: uv run python data/fetch_pokeapi.py"
        )
    with open(_POKEMON_DATA_PATH) as f:
        raw = json.load(f)
    return [Pokemon.model_validate(p) for p in raw]


def _normalize_game_slug(name: str) -> str:
    """Normalize a display game name to a lowercase alphanumeric slug.

    Handles frontend title-case names like "FireRed", "Ultra Sun", "Let's Go Pikachu"
    → backend slugs "firered", "ultrasun", "letsgopikachu".
    """
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _resolve_games(request: OptimizeRequest) -> list[str]:
    """
    Expand the request's generation + game selection into a concrete list of game slugs.
    If specific games are named, normalize to lowercase slugs first.
    Otherwise, use all games in selected gens.
    """
    if request.games:
        return [_normalize_game_slug(g) for g in request.games]
    games: list[str] = []
    for gen in request.generations:
        games.extend(GEN_TO_GAMES.get(gen, []))
    return games


def _is_available_in_games(
    pokemon: Pokemon,
    games: list[str],
    mode: AvailabilityMode,
) -> bool:
    """
    Check whether a Pokemon is eligible given the selected games and availability mode.

    The availability dict maps game_slug → AvailabilityTier.
    We take the BEST (most permissive) tier across all selected games.
    """
    if not games or not pokemon.availability:
        # No game data: default to gen-based inclusion (competitive mode only)
        return mode == AvailabilityMode.COMPETITIVE

    best_tier: AvailabilityTier | None = None
    tier_rank = {
        AvailabilityTier.WILD:         0,
        AvailabilityTier.TRADEABLE:    1,
        AvailabilityTier.EVENT:        2,
        AvailabilityTier.TRANSFER:     3,
        AvailabilityTier.UNOBTAINABLE: 4,
    }

    for game in games:
        tier = pokemon.availability.get(game, AvailabilityTier.UNOBTAINABLE)
        if best_tier is None or tier_rank[tier] < tier_rank[best_tier]:
            best_tier = tier

    if best_tier is None or best_tier == AvailabilityTier.UNOBTAINABLE:
        return False

    if mode == AvailabilityMode.COMPETITIVE:
        # Include everything except UNOBTAINABLE
        return True
    elif mode == AvailabilityMode.CARTRIDGE:
        return best_tier in {AvailabilityTier.WILD, AvailabilityTier.TRADEABLE}
    elif mode == AvailabilityMode.SOLO_RUN:
        return best_tier == AvailabilityTier.WILD
    return False


def build_eligible_pool(request: OptimizeRequest) -> list[Pokemon]:
    """
    Apply all filters from the OptimizeRequest and return the eligible Pokemon pool.

    Filters applied (in order):
      1. Generation / game filter (which Pokemon exist in the selected games)
      2. Availability mode (COMPETITIVE / CARTRIDGE / SOLO_RUN)
      3. Legendary / mythical toggle
      4. Minimum base stat total
      5. Required types (pool must contain at least one of each required type,
         but individual Pokemon don't all need the required type)

    Anchor Pokemon bypass all filters except generation/game — they are always included
    if the user explicitly named them.
    """
    all_pokemon = load_all_pokemon()
    games = _resolve_games(request)
    anchor_names = set(request.anchor_pokemon)

    # Determine which gens are in scope (for gen-only filtering when no availability data)
    selected_gens = set(request.generations)

    eligible: list[Pokemon] = []

    for p in all_pokemon:
        is_anchor = p.name in anchor_names

        # Anchors skip most filters but must be in the right gen/game scope
        if is_anchor:
            eligible.append(p)
            continue

        # 0. Exclude battle-only / cosmetic-only alternate forms.
        # Regional variants are only included when the generation that introduced them is selected.
        _name = p.name
        if (
            "-mega" in _name          # Mega Evolutions
            or "-gmax" in _name       # Gigantamax
            or "-primal" in _name     # Primal Reversions
            or "-totem" in _name      # Totem forms
            or "-cap" in _name        # Pikachu cap variants
            or _name in {"pikachu-starter", "eevee-starter"}
        ):
            continue

        # Regional variants: only include when the originating region's generation is selected.
        # Alolan forms = Gen 7, Galarian/Hisuian = Gen 8, Paldean = Gen 9.
        _REGIONAL_GEN: dict[str, int] = {
            "-alola": 7,
            "-galar": 8,
            "-hisui": 8,
            "-paldea": 9,
        }
        _skip = False
        for suffix, min_gen in _REGIONAL_GEN.items():
            if suffix in _name and min_gen not in selected_gens:
                _skip = True
                break
        if _skip:
            continue

        # 1. Generation/game scope
        if p.generation not in selected_gens and selected_gens:
            continue

        # 2. Availability mode — COMPETITIVE means "full national dex", skip availability check.
        # Only CARTRIDGE / SOLO_RUN need game-specific availability filtering.
        if request.availability_mode != AvailabilityMode.COMPETITIVE:
            if pokemon_has_availability_data(p):
                if not _is_available_in_games(p, games, request.availability_mode):
                    continue

        # 3. Legendary/mythical filter
        if not request.allow_legendaries and (p.is_legendary or p.is_mythical):
            continue

        # 4. Minimum BST
        if p.bst < request.min_bst:
            continue

        eligible.append(p)

    # 5. Required types: warn if pool doesn't contain any Pokemon of a required type
    # (we don't hard-exclude here — the solver handles the constraint)
    for req_type in request.required_types:
        if not any(req_type in p.types for p in eligible):
            raise ValueError(
                f"No eligible Pokemon of type {req_type.value} found in the current pool. "
                "Try relaxing filters (e.g., allow legendaries, expand generations)."
            )

    return eligible


def pokemon_has_availability_data(p: Pokemon) -> bool:
    return bool(p.availability)


def validate_team(
    team_names: list[str],
    request: OptimizeRequest,
    pool: list[Pokemon],
) -> list[str]:
    """
    Validate that a proposed team satisfies all hard constraints.

    Returns a list of violation messages (empty list = valid).
    """
    violations: list[str] = []
    pool_by_name = {p.name: p for p in pool}
    team = [pool_by_name[name] for name in team_names if name in pool_by_name]

    # Team size
    if len(team) != 6:
        violations.append(f"Team has {len(team)} members, expected 6.")

    # No duplicates
    if len(set(team_names)) != len(team_names):
        violations.append("Team contains duplicate Pokemon.")

    # All anchors present
    for anchor in request.anchor_pokemon:
        if anchor not in team_names:
            violations.append(f"Anchor Pokemon '{anchor}' is missing from the team.")

    # Required types
    team_types: set[PokemonType] = set()
    for p in team:
        team_types.update(p.types)
    for req_type in request.required_types:
        if req_type not in team_types:
            violations.append(f"Team has no Pokemon of required type {req_type.value}.")

    # Legendary constraint
    if not request.allow_legendaries:
        for p in team:
            if p.is_legendary or p.is_mythical:
                violations.append(
                    f"{p.display_name} is legendary/mythical but legendaries are disabled."
                )

    return violations
