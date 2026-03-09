"""
optimizer/ga_solver.py — Genetic Algorithm solver for team optimization.

Design
------
Each chromosome is a sorted tuple of 6 Pokemon indices from the eligible pool.
No duplicate entries within a chromosome (each Pokemon appears at most once).

Algorithm:
  1. Initialize population of `POP_SIZE` random valid teams
  2. Evaluate fitness for each chromosome (composite team score)
  3. Repeat for `MAX_GENERATIONS` generations (or until convergence):
     a. Elitism: preserve top `ELITE_SIZE` chromosomes unchanged
     b. Tournament selection: pick parents for crossover
     c. Uniform crossover: merge two parent teams, repair duplicates
     d. Mutation: randomly swap one team member with a pool Pokemon
     e. Evaluate fitness of new population
  4. Return the best chromosome found

The GA is implemented as a generator so the FastAPI endpoint can stream
generation-by-generation fitness updates via Server-Sent Events.
"""

from __future__ import annotations

import random
import time
from collections.abc import Generator
from dataclasses import dataclass, field

from optimizer.constraints import build_eligible_pool
from optimizer.models import (
    OptimizeRequest,
    OptimizeResponse,
    Pokemon,
    ScoreWeights,
    Team,
    TeamMember,
)
from optimizer.scoring import score_team

# ---------------------------------------------------------------------------
# Hyperparameters (all tunable)
# ---------------------------------------------------------------------------
POP_SIZE      = 200    # Number of chromosomes in the population
MAX_GENS      = 500    # Maximum generations to run
ELITE_SIZE    = 10     # Top N chromosomes preserved unchanged each generation
TOURNAMENT_K  = 5      # Tournament selection size
MUTATION_RATE = 0.15   # Probability of mutating one slot per chromosome
PATIENCE      = 60     # Stop early if no improvement for this many generations


@dataclass
class Chromosome:
    """A candidate team — indices into the pool list."""
    indices: tuple[int, ...]          # Exactly 6 unique indices
    fitness: float = 0.0


@dataclass
class GenerationStats:
    """Emitted at the end of each generation for SSE streaming."""
    generation: int
    best_fitness: float
    mean_fitness: float
    best_team_names: list[str]
    converged: bool = False


def _fitness(
    indices: tuple[int, ...],
    pool: list[Pokemon],
    weights: ScoreWeights,
    request: OptimizeRequest,
) -> float:
    members = [TeamMember(pokemon=pool[i]) for i in indices]
    score, _ = score_team(members, weights, request.play_style, request.weather_condition)
    return score


def _random_chromosome(
    pool_size: int,
    anchor_indices: list[int],
    rng: random.Random,
) -> tuple[int, ...]:
    """Generate a random valid chromosome, respecting anchor constraints."""
    non_anchor = list(set(range(pool_size)) - set(anchor_indices))
    rng.shuffle(non_anchor)
    needed = 6 - len(anchor_indices)
    chosen = anchor_indices + non_anchor[:needed]
    return tuple(sorted(chosen))


def _tournament_select(population: list[Chromosome], k: int, rng: random.Random) -> Chromosome:
    """Return the fittest chromosome from k randomly selected candidates."""
    candidates = rng.choices(population, k=k)
    return max(candidates, key=lambda c: c.fitness)


def _crossover(
    parent_a: Chromosome,
    parent_b: Chromosome,
    anchor_indices: set[int],
    pool_size: int,
    rng: random.Random,
) -> tuple[int, ...]:
    """
    Uniform crossover: for each slot, randomly pick from parent A or B.
    Repair duplicates by filling from the remaining pool at random.

    Anchor indices are always included.
    """
    # Collect candidates from both parents
    combined = list(set(parent_a.indices) | set(parent_b.indices))
    rng.shuffle(combined)

    # Always keep anchors
    child_set: set[int] = set(anchor_indices)
    for idx in combined:
        if len(child_set) == 6:
            break
        child_set.add(idx)

    # If still short (unlikely but possible), fill randomly
    while len(child_set) < 6:
        candidate = rng.randrange(pool_size)
        child_set.add(candidate)

    return tuple(sorted(child_set))


def _mutate(
    indices: tuple[int, ...],
    anchor_indices: set[int],
    pool_size: int,
    rng: random.Random,
) -> tuple[int, ...]:
    """Replace one non-anchor team member with a random pool Pokemon."""
    mutable = [i for i in indices if i not in anchor_indices]
    if not mutable:
        return indices  # All slots are anchors — nothing to mutate

    # Pick a random non-anchor slot to replace
    to_replace = rng.choice(mutable)
    current_set = set(indices)
    current_set.discard(to_replace)

    # Pick a random replacement not already on the team
    available = list(set(range(pool_size)) - current_set)
    if not available:
        return indices
    replacement = rng.choice(available)
    current_set.add(replacement)
    return tuple(sorted(current_set))


def run_ga(
    request: OptimizeRequest,
    seed: int | None = None,
) -> Generator[GenerationStats, None, Team]:
    """
    Run the genetic algorithm. Yields GenerationStats after each generation.
    Returns the best Team found when the generator is exhausted.

    Usage (sync):
        gen = run_ga(request)
        try:
            while True:
                stats = next(gen)
                print(stats)
        except StopIteration as e:
            best_team = e.value

    Usage (async, for SSE streaming):
        for stats in run_ga(request):
            await sse_send(stats)
    """
    t0 = time.perf_counter()
    rng = random.Random(seed)

    pool = build_eligible_pool(request)
    if len(pool) < 6:
        raise ValueError(f"Pool has only {len(pool)} eligible Pokemon (need at least 6).")

    weights = request.weights or ScoreWeights.for_play_style(request.play_style)
    anchor_names = set(request.anchor_pokemon)
    anchor_indices = [i for i, p in enumerate(pool) if p.name in anchor_names]
    anchor_index_set = set(anchor_indices)

    if len(anchor_indices) > 5:
        raise ValueError("Too many anchor Pokemon (max 5). The GA needs at least 1 free slot.")

    # ---------------------------------------------------------------------------
    # Initialize population
    # ---------------------------------------------------------------------------
    population: list[Chromosome] = []
    for _ in range(POP_SIZE):
        indices = _random_chromosome(len(pool), anchor_indices, rng)
        fitness = _fitness(indices, pool, weights, request)
        population.append(Chromosome(indices=indices, fitness=fitness))

    population.sort(key=lambda c: c.fitness, reverse=True)
    best_ever = population[0]
    no_improve_count = 0

    # ---------------------------------------------------------------------------
    # Evolution loop
    # ---------------------------------------------------------------------------
    for gen in range(1, MAX_GENS + 1):
        next_gen: list[Chromosome] = []

        # Elitism: carry over top chromosomes unchanged
        next_gen.extend(population[:ELITE_SIZE])

        # Fill rest of next generation
        while len(next_gen) < POP_SIZE:
            parent_a = _tournament_select(population, TOURNAMENT_K, rng)
            parent_b = _tournament_select(population, TOURNAMENT_K, rng)

            child_indices = _crossover(parent_a, parent_b, anchor_index_set, len(pool), rng)

            if rng.random() < MUTATION_RATE:
                child_indices = _mutate(child_indices, anchor_index_set, len(pool), rng)

            fitness = _fitness(child_indices, pool, weights, request)
            next_gen.append(Chromosome(indices=child_indices, fitness=fitness))

        next_gen.sort(key=lambda c: c.fitness, reverse=True)
        population = next_gen

        # Track improvement
        if population[0].fitness > best_ever.fitness:
            best_ever = population[0]
            no_improve_count = 0
        else:
            no_improve_count += 1

        converged = no_improve_count >= PATIENCE
        mean_fitness = sum(c.fitness for c in population) / POP_SIZE

        stats = GenerationStats(
            generation=gen,
            best_fitness=round(best_ever.fitness, 2),
            mean_fitness=round(mean_fitness, 2),
            best_team_names=[pool[i].name for i in best_ever.indices],
            converged=converged,
        )
        yield stats

        if converged:
            break

    # ---------------------------------------------------------------------------
    # Build the final Team object
    # ---------------------------------------------------------------------------
    solve_time = time.perf_counter() - t0
    selected = [pool[i] for i in best_ever.indices]
    members = [
        TeamMember(pokemon=p, is_anchor=(p.name in anchor_names))
        for p in selected
    ]
    composite, breakdown = score_team(members, weights, request.play_style, request.weather_condition)

    return Team(
        members=members,
        score=composite,
        score_breakdown=breakdown,
        solver="genetic",
        solve_time_seconds=round(solve_time, 3),
    )


def solve(request: OptimizeRequest, seed: int | None = None) -> tuple[Team, list[GenerationStats]]:
    """
    Synchronous wrapper: run the GA to completion, collect all generation stats.
    Returns (best_team, all_generation_stats).
    """
    gen = run_ga(request, seed=seed)
    all_stats: list[GenerationStats] = []
    try:
        while True:
            stats = next(gen)
            all_stats.append(stats)
    except StopIteration as e:
        return e.value, all_stats


def solve_and_respond(
    request: OptimizeRequest,
    seed: int | None = None,
) -> tuple[OptimizeResponse, list[GenerationStats]]:
    pool = build_eligible_pool(request)
    team, stats = solve(request, seed=seed)
    return (
        OptimizeResponse(request=request, teams={"genetic": team}, pool_size=len(pool)),
        stats,
    )
