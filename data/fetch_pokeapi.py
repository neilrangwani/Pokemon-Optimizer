"""
fetch_pokeapi.py — Build the static Pokemon dataset from PokéAPI.

Fetches all Pokemon, enriches with availability tiers (WILD/TRADEABLE/EVENT/TRANSFER/UNOBTAINABLE),
and writes pokemon.json. Run this once to build the dataset; the optimizer never calls the API at runtime.

Usage:
    uv run python data/fetch_pokeapi.py
    uv run python data/fetch_pokeapi.py --gen 1 3   # only Gen 1–3
    uv run python data/fetch_pokeapi.py --limit 50   # first 50 for dev/testing
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

BASE_URL = "https://pokeapi.co/api/v2"
OUT_FILE = Path(__file__).parent / "pokemon.json"
EVENT_FILE = Path(__file__).parent / "event_pokemon.json"

# Maps PokéAPI game version names to our canonical game slugs and generation numbers.
GAME_VERSIONS: dict[str, tuple[str, int]] = {
    "red":               ("red",                1),
    "blue":              ("blue",               1),
    "yellow":            ("yellow",             1),
    "gold":              ("gold",               2),
    "silver":            ("silver",             2),
    "crystal":           ("crystal",            2),
    "ruby":              ("ruby",               3),
    "sapphire":          ("sapphire",           3),
    "emerald":           ("emerald",            3),
    "firered":           ("firered",            3),
    "leafgreen":         ("leafgreen",          3),
    "diamond":           ("diamond",            4),
    "pearl":             ("pearl",              4),
    "platinum":          ("platinum",           4),
    "heartgold":         ("heartgold",          4),
    "soulsilver":        ("soulsilver",         4),
    "black":             ("black",              5),
    "white":             ("white",              5),
    "black-2":           ("black2",             5),
    "white-2":           ("white2",             5),
    "x":                 ("x",                  6),
    "y":                 ("y",                  6),
    "omega-ruby":        ("omegaruby",           6),
    "alpha-sapphire":    ("alphasapphire",       6),
    "sun":               ("sun",                7),
    "moon":              ("moon",               7),
    "ultra-sun":         ("ultrasun",           7),
    "ultra-moon":        ("ultramoon",          7),
    "lets-go-pikachu":   ("letsgopikachu",      7),
    "lets-go-eevee":     ("letsgoeevee",        7),
    "sword":             ("sword",              8),
    "shield":            ("shield",             8),
    "brilliant-diamond": ("brilliantdiamond",   8),
    "shining-pearl":     ("shiningpearl",       8),
    "legends-arceus":    ("legendsarceus",      8),
    "scarlet":           ("scarlet",            9),
    "violet":            ("violet",             9),
}

# Version exclusives: maps each game to its paired counterpart.
# If both are selected, exclusives become TRADEABLE instead of excluded.
VERSION_PAIRS: list[tuple[str, str]] = [
    ("red",           "blue"),
    ("gold",          "silver"),
    ("ruby",          "sapphire"),
    ("firered",       "leafgreen"),
    ("diamond",       "pearl"),
    ("heartgold",     "soulsilver"),
    ("black",         "white"),
    ("black2",        "white2"),
    ("x",             "y"),
    ("omegaruby",     "alphasapphire"),
    ("sun",           "moon"),
    ("ultrasun",      "ultramoon"),
    ("letsgopikachu", "letsgoeevee"),
    ("sword",         "shield"),
    ("brilliantdiamond", "shiningpearl"),
    ("scarlet",       "violet"),
]

# Trade evolution Pokemon — always TRADEABLE regardless of other factors.
# These are species that can only evolve via trade (with or without held item).
TRADE_EVOLUTIONS: set[str] = {
    "alakazam", "machamp", "gengar", "golem",            # Gen 1
    "politoed", "slowking", "steelix", "scizor",          # Gen 2
    "kingdra", "porygon2", "porygon-z",
    "huntail", "gorebyss", "milotic",                     # Gen 3
    "rhyperior", "electivire", "magmortar",               # Gen 4
    "togekiss", "yanmega", "ambipom", "lickilicky",
    "tangrowth", "mamoswine",
    "escavalier", "accelgor",                             # Gen 5
    "conkeldurr", "gurdurr",
    "karrablast", "shelmet",
}

# Type colors for reference (used by frontend but stored here for completeness)
TYPE_COLORS: dict[str, str] = {
    "Normal": "#A8A77A", "Fire": "#EE8130", "Water": "#6390F0",
    "Electric": "#F7D02C", "Grass": "#7AC74C", "Ice": "#96D9D6",
    "Fighting": "#C22E28", "Poison": "#A33EA1", "Ground": "#E2BF65",
    "Flying": "#A98FF3", "Psychic": "#F95587", "Bug": "#A6B91A",
    "Rock": "#B6A136", "Ghost": "#735797", "Dragon": "#6F35FC",
    "Dark": "#705746", "Steel": "#B7B7CE", "Fairy": "#D685AD",
}


def load_event_pokemon() -> dict:
    if not EVENT_FILE.exists():
        print(f"[warn] {EVENT_FILE} not found — no EVENT tier will be applied.")
        return {}
    with open(EVENT_FILE) as f:
        return json.load(f)


def get_availability(
    name: str,
    game_indices: list[dict],
    event_data: dict,
) -> dict[str, str]:
    """
    Derive availability tier per game for a single Pokemon.

    Returns: { game_slug: "WILD" | "TRADEABLE" | "EVENT" | "TRANSFER" | "UNOBTAINABLE" }

    Priority chain:
      1. Not in game-indices → UNOBTAINABLE
      2. In event_pokemon.json for this game → EVENT
      3. Is a trade evolution species → TRADEABLE
      4. Has location data in game-indices (game_index > 0) → WILD
      5. In game-indices but index == 0 (transfer only) → TRANSFER
    """
    # Build set of games where this Pokemon appears
    appears_in: set[str] = set()
    for entry in game_indices:
        version_name = entry.get("version", {}).get("name", "")
        if version_name in GAME_VERSIONS:
            canonical, _ = GAME_VERSIONS[version_name]
            appears_in.add(canonical)

    event_info = event_data.get(name, {})
    event_games: set[str] = set(event_info.get("event_games", []))
    non_event_games: set[str] = set(event_info.get("non_event_games", []))
    is_trade_evo = name in TRADE_EVOLUTIONS

    result: dict[str, str] = {}
    all_games = {canonical for canonical, _ in GAME_VERSIONS.values()}

    for game in all_games:
        if game not in appears_in:
            result[game] = "UNOBTAINABLE"
        elif game in event_games and game not in non_event_games:
            result[game] = "EVENT"
        elif is_trade_evo:
            result[game] = "TRADEABLE"
        else:
            result[game] = "WILD"

    return result


async def fetch_json(client: httpx.AsyncClient, url: str) -> dict:
    for attempt in range(3):
        try:
            r = await client.get(url, timeout=30.0)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)
    return {}


async def fetch_pokemon_detail(
    client: httpx.AsyncClient,
    url: str,
    event_data: dict,
    gen_filter: set[int] | None,
) -> dict | None:
    data = await fetch_json(client, url)

    # Determine generation from game_indices
    gen_nums = set()
    for entry in data.get("game_indices", []):
        v = entry.get("version", {}).get("name", "")
        if v in GAME_VERSIONS:
            gen_nums.add(GAME_VERSIONS[v][1])

    # Also infer from species URL (more reliable for newer gens)
    species_url = data.get("species", {}).get("url", "")

    if gen_filter and not any(g in gen_filter for g in gen_nums) and gen_nums:
        return None

    # Fetch species for legendary/mythical flags and generation
    species = {}
    if species_url:
        try:
            species = await fetch_json(client, species_url)
        except Exception:
            pass

    generation_name = species.get("generation", {}).get("name", "")
    _ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9}
    _gen_suffix = generation_name.split("-")[-1] if generation_name else ""
    gen_number = _ROMAN.get(_gen_suffix) or (int(_gen_suffix) if _gen_suffix.isdigit() else 0)
    if gen_filter and gen_number and gen_number not in gen_filter:
        return None

    # Base stats
    stats_raw = {s["stat"]["name"]: s["base_stat"] for s in data.get("stats", [])}
    stats = {
        "hp":      stats_raw.get("hp", 0),
        "attack":  stats_raw.get("attack", 0),
        "defense": stats_raw.get("defense", 0),
        "sp_atk":  stats_raw.get("special-attack", 0),
        "sp_def":  stats_raw.get("special-defense", 0),
        "speed":   stats_raw.get("speed", 0),
    }
    stats["total"] = sum(stats.values())

    # Types
    types = [t["type"]["name"].capitalize() for t in data.get("types", [])]

    # Abilities
    abilities = [
        {
            "name": a["ability"]["name"],
            "is_hidden": a["is_hidden"],
        }
        for a in data.get("abilities", [])
    ]

    # Sprites — prefer Gen 3 / FRLG sprites for the UI aesthetic
    sprites_raw = data.get("sprites", {})
    gen3_sprites = (
        sprites_raw.get("versions", {})
        .get("generation-iii", {})
        .get("firered-leafgreen", {})
    )
    sprite_url = (
        gen3_sprites.get("front_default")
        or sprites_raw.get("front_default")
        or ""
    )

    # Availability tiers
    availability = get_availability(
        data["name"],
        data.get("game_indices", []),
        event_data,
    )

    return {
        "id": data["id"],
        "name": data["name"],
        "display_name": next(
            (n["name"] for n in species.get("names", []) if n.get("language", {}).get("name") == "en"),
            data["name"].replace("-", " ").title(),
        ),
        "generation": gen_number,
        "types": types,
        "stats": stats,
        "abilities": abilities,
        "sprite_url": sprite_url,
        "is_legendary": species.get("is_legendary", False),
        "is_mythical": species.get("is_mythical", False),
        "availability": availability,
    }


async def main(gen_filter: set[int] | None = None, limit: int | None = None) -> None:
    event_data = load_event_pokemon()

    print("Fetching Pokemon list from PokéAPI...")
    async with httpx.AsyncClient(
        headers={"User-Agent": "PokemonTeamOptimizer/1.0 (portfolio project)"},
        follow_redirects=True,
    ) as client:
        # Fetch full list (PokéAPI has ~1025 Pokemon as of Gen 9)
        list_data = await fetch_json(
            client, f"{BASE_URL}/pokemon?limit={limit or 1500}&offset=0"
        )
        entries = list_data.get("results", [])
        if limit:
            entries = entries[:limit]

        print(f"Found {len(entries)} Pokemon. Fetching details...")

        # Semaphore to stay well within PokéAPI rate limits (60 req/min)
        sem = asyncio.Semaphore(10)

        async def fetch_with_sem(url: str) -> dict | None:
            async with sem:
                return await fetch_pokemon_detail(client, url, event_data, gen_filter)

        tasks = [fetch_with_sem(e["url"]) for e in entries]
        results = []
        for i, coro in enumerate(asyncio.as_completed(tasks), 1):
            result = await coro
            if result:
                results.append(result)
            if i % 50 == 0:
                print(f"  {i}/{len(tasks)} fetched, {len(results)} kept...")

    # Sort by dex number
    results.sort(key=lambda p: p["id"])
    print(f"\nWriting {len(results)} Pokemon to {OUT_FILE}...")
    with open(OUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Pokemon data from PokéAPI.")
    parser.add_argument(
        "--gen", nargs="+", type=int, metavar="N",
        help="Only include these generation numbers (e.g. --gen 1 2 3)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Cap total Pokemon fetched (useful for local dev/testing)"
    )
    args = parser.parse_args()

    gen_filter = set(args.gen) if args.gen else None
    asyncio.run(main(gen_filter=gen_filter, limit=args.limit))
