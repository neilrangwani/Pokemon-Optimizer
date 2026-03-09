"""
api/main.py — FastAPI server for the Pokemon Team Optimizer.

Endpoints
---------
POST /optimize          — Run ILP, GA, or Greedy (or all) and return results.
POST /optimize/stream   — Stream GA generation-by-generation updates via SSE.
GET  /pokemon           — Return the full eligible pool for a given request config.
GET  /health            — Health check.

The SSE endpoint is the key one for the UI's GA animation panel.
It streams JSON-encoded GenerationStats objects, then a final "done" event
with the complete Team result.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from optimizer import ga_solver, greedy_solver, ilp_solver
from optimizer.constraints import build_eligible_pool, load_all_pokemon
from optimizer.scoring import classify_role
from optimizer.models import (
    OptimizeRequest,
    OptimizeResponse,
    Pokemon,
    ScoreWeights,
    Team,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-load Pokemon data on startup so first request is fast
    try:
        load_all_pokemon()
    except FileNotFoundError:
        print(
            "[warn] pokemon.json not found. Run: uv run python data/fetch_pokeapi.py\n"
            "       Optimizer endpoints will fail until data is built."
        )
    yield


app = FastAPI(
    title="Pokemon Team Optimizer API",
    description="Multi-objective combinatorial optimizer for Pokemon team composition.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Pokemon pool endpoint
# ---------------------------------------------------------------------------

class PoolRequest(BaseModel):
    generations: list[int] = list(range(1, 10))
    games: list[str] = []
    availability_mode: str = "COMPETITIVE"
    allow_legendaries: bool = False
    min_bst: int = 0


@app.post("/pokemon/pool", response_model=list[dict])
async def get_pool(req: PoolRequest):
    """Return the filtered Pokemon pool for the given constraints (no optimization)."""
    from optimizer.models import AvailabilityMode

    opt_req = OptimizeRequest(
        generations=req.generations,
        games=req.games,
        availability_mode=AvailabilityMode(req.availability_mode),
        allow_legendaries=req.allow_legendaries,
        min_bst=req.min_bst,
    )
    pool = build_eligible_pool(opt_req)
    return [
        {
            "id": p.id,
            "name": p.name,
            "display_name": p.display_name,
            "generation": p.generation,
            "types": [t.value for t in p.types],
            "bst": p.bst,
            "stats": p.stats.model_dump(),
            "sprite_url": p.sprite_url,
            "is_legendary": p.is_legendary,
            "is_mythical": p.is_mythical,
        }
        for p in pool
    ]


# ---------------------------------------------------------------------------
# Synchronous optimization (ILP + Greedy, and GA without streaming)
# ---------------------------------------------------------------------------

@app.post("/optimize", response_model=dict)
async def optimize(request: OptimizeRequest):
    """
    Run optimization with the specified solver(s). Returns all results at once.
    For GA with live animation, use POST /optimize/stream instead.
    """
    results: dict[str, dict] = {}
    pool = build_eligible_pool(request)

    if request.solver in ("ilp", "all"):
        try:
            team, _ = await asyncio.to_thread(ilp_solver.solve, request)
            results["ilp"] = _team_to_dict(team)
        except Exception as e:
            results["ilp"] = {"error": str(e)}

    if request.solver in ("greedy", "all"):
        try:
            team, _ = await asyncio.to_thread(greedy_solver.solve, request)
            results["greedy"] = _team_to_dict(team)
        except Exception as e:
            results["greedy"] = {"error": str(e)}

    if request.solver in ("genetic", "all"):
        try:
            team, stats = await asyncio.to_thread(ga_solver.solve, request)
            results["genetic"] = _team_to_dict(team)
            results["genetic"]["generation_history"] = [
                {
                    "generation": s.generation,
                    "best_fitness": s.best_fitness,
                    "mean_fitness": s.mean_fitness,
                }
                for s in stats
            ]
        except Exception as e:
            results["genetic"] = {"error": str(e)}

    return {
        "pool_size": len(pool),
        "results": results,
    }


# ---------------------------------------------------------------------------
# SSE streaming endpoint for GA animation
# ---------------------------------------------------------------------------

@app.post("/optimize/stream")
async def optimize_stream(request: OptimizeRequest):
    """
    Stream GA generation statistics via Server-Sent Events.

    Event types:
      "generation" — GenerationStats JSON (one per generation)
      "done"       — Final Team JSON when GA completes
      "error"      — Error message string

    Frontend connects with EventSource and listens for these event types.
    """
    async def event_generator():
        try:
            pool = build_eligible_pool(request)
            yield {
                "event": "pool_size",
                "data": json.dumps({"pool_size": len(pool)}),
            }

            gen = ga_solver.run_ga(request)
            final_team: Team | None = None

            # asyncio.to_thread wraps StopIteration in RuntimeError; use sentinel instead
            _DONE = object()

            def _next_or_done():
                try:
                    return next(gen)
                except StopIteration as e:
                    return (e.value, _DONE)

            while True:
                result = await asyncio.to_thread(_next_or_done)
                if isinstance(result, tuple) and len(result) == 2 and result[1] is _DONE:
                    final_team = result[0]
                    break
                stats = result
                yield {
                    "event": "generation",
                    "data": json.dumps({
                        "generation": stats.generation,
                        "best_fitness": stats.best_fitness,
                        "mean_fitness": stats.mean_fitness,
                        "best_team_names": stats.best_team_names,
                        "converged": stats.converged,
                    }),
                }
                await asyncio.sleep(0)

            if final_team:
                yield {
                    "event": "done",
                    "data": json.dumps(_team_to_dict(final_team)),
                }

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}),
            }

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Score a user-provided team (for comparison mode)
# ---------------------------------------------------------------------------

class ScoreRequest(BaseModel):
    pokemon_names: list[str]
    play_style: str = "BALANCED"
    weights: dict[str, float] | None = None


@app.post("/score")
async def score_team_endpoint(req: ScoreRequest):
    """Score an arbitrary team provided by the user. Used for comparison mode."""
    from optimizer.models import PlayStyle
    from optimizer.scoring import score_team
    from optimizer.models import TeamMember

    all_pokemon = {p.name: p for p in load_all_pokemon()}
    members = []
    missing = []
    for name in req.pokemon_names:
        if name in all_pokemon:
            members.append(TeamMember(pokemon=all_pokemon[name]))
        else:
            missing.append(name)

    if missing:
        raise HTTPException(status_code=404, detail=f"Unknown Pokemon: {missing}")
    if len(members) > 6:
        raise HTTPException(status_code=400, detail="Maximum 6 Pokemon per team.")

    try:
        play_style = PlayStyle(req.play_style)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid play_style: {req.play_style}")

    weights = ScoreWeights.for_play_style(play_style)
    if req.weights:
        weights = ScoreWeights(**req.weights)

    composite, breakdown = score_team(members, weights, play_style)
    return {
        "score": composite,
        "breakdown": breakdown,
        "team": [
            {
                "name": m.pokemon.name,
                "display_name": m.pokemon.display_name,
                "types": [t.value for t in m.pokemon.types],
                "bst": m.pokemon.bst,
                "sprite_url": m.pokemon.sprite_url,
            }
            for m in members
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _team_to_dict(team: Team) -> dict:
    return {
        "score": team.score,
        "score_breakdown": team.score_breakdown,
        "solver": team.solver,
        "solve_time_seconds": team.solve_time_seconds,
        "members": [
            {
                "name": m.pokemon.name,
                "display_name": m.pokemon.display_name,
                "types": [t.value for t in m.pokemon.types],
                "bst": m.pokemon.bst,
                "stats": m.pokemon.stats.model_dump(),
                "sprite_url": m.pokemon.sprite_url,
                "is_legendary": m.pokemon.is_legendary,
                "is_mythical": m.pokemon.is_mythical,
                "is_anchor": m.is_anchor,
                "abilities": [{"name": a.name, "is_hidden": a.is_hidden} for a in m.pokemon.abilities],
                "role": classify_role(m.pokemon).value,
            }
            for m in team.members
        ],
    }
