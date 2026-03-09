import type { PokemonType } from "../types";

/**
 * Full 18×18 type effectiveness chart.
 * TYPE_CHART[attacker][defender] = damage multiplier (0 | 0.5 | 1 | 2).
 *
 * Use netEffectiveness() for dual-type defenders — it multiplies both slots
 * and correctly handles cancellations (e.g. Water/Flying vs Ice = 0.5×2 = 1×, not 2×)
 * and 4× weaknesses (e.g. Golem Rock/Ground vs Grass = 2×2 = 4×, still 1 Pokémon).
 */
export const TYPE_CHART: Record<PokemonType, Record<PokemonType, number>> = {
  Normal:   { Normal:1, Fire:1,   Water:1,   Grass:1,   Electric:1,   Ice:1,   Fighting:1,   Poison:1,   Ground:1,   Flying:1,   Psychic:1,   Bug:1,   Rock:0.5, Ghost:0,   Dragon:1,   Dark:1,   Steel:0.5, Fairy:1   },
  Fire:     { Normal:1, Fire:0.5, Water:0.5, Grass:2,   Electric:1,   Ice:2,   Fighting:1,   Poison:1,   Ground:1,   Flying:1,   Psychic:1,   Bug:2,   Rock:0.5, Ghost:1,   Dragon:0.5, Dark:1,   Steel:2,   Fairy:1   },
  Water:    { Normal:1, Fire:2,   Water:0.5, Grass:0.5, Electric:1,   Ice:1,   Fighting:1,   Poison:1,   Ground:2,   Flying:1,   Psychic:1,   Bug:1,   Rock:2,   Ghost:1,   Dragon:0.5, Dark:1,   Steel:1,   Fairy:1   },
  Grass:    { Normal:1, Fire:0.5, Water:2,   Grass:0.5, Electric:1,   Ice:1,   Fighting:1,   Poison:0.5, Ground:2,   Flying:0.5, Psychic:1,   Bug:0.5, Rock:2,   Ghost:1,   Dragon:0.5, Dark:1,   Steel:0.5, Fairy:1   },
  Electric: { Normal:1, Fire:1,   Water:2,   Grass:0.5, Electric:0.5, Ice:1,   Fighting:1,   Poison:1,   Ground:0,   Flying:2,   Psychic:1,   Bug:1,   Rock:1,   Ghost:1,   Dragon:0.5, Dark:1,   Steel:1,   Fairy:1   },
  Ice:      { Normal:1, Fire:0.5, Water:0.5, Grass:2,   Electric:1,   Ice:0.5, Fighting:1,   Poison:1,   Ground:2,   Flying:2,   Psychic:1,   Bug:1,   Rock:1,   Ghost:1,   Dragon:2,   Dark:1,   Steel:0.5, Fairy:1   },
  Fighting: { Normal:2, Fire:1,   Water:1,   Grass:1,   Electric:1,   Ice:2,   Fighting:1,   Poison:0.5, Ground:1,   Flying:0.5, Psychic:0.5, Bug:0.5, Rock:2,   Ghost:0,   Dragon:1,   Dark:2,   Steel:2,   Fairy:0.5 },
  Poison:   { Normal:1, Fire:1,   Water:1,   Grass:2,   Electric:1,   Ice:1,   Fighting:1,   Poison:0.5, Ground:0.5, Flying:1,   Psychic:1,   Bug:1,   Rock:0.5, Ghost:0.5, Dragon:1,   Dark:1,   Steel:0,   Fairy:2   },
  Ground:   { Normal:1, Fire:2,   Water:1,   Grass:0.5, Electric:2,   Ice:1,   Fighting:1,   Poison:2,   Ground:1,   Flying:0,   Psychic:1,   Bug:0.5, Rock:2,   Ghost:1,   Dragon:1,   Dark:1,   Steel:2,   Fairy:1   },
  Flying:   { Normal:1, Fire:1,   Water:1,   Grass:2,   Electric:0.5, Ice:1,   Fighting:2,   Poison:1,   Ground:1,   Flying:1,   Psychic:1,   Bug:2,   Rock:0.5, Ghost:1,   Dragon:1,   Dark:1,   Steel:0.5, Fairy:1   },
  Psychic:  { Normal:1, Fire:1,   Water:1,   Grass:1,   Electric:1,   Ice:1,   Fighting:2,   Poison:2,   Ground:1,   Flying:1,   Psychic:0.5, Bug:1,   Rock:1,   Ghost:1,   Dragon:1,   Dark:0,   Steel:0.5, Fairy:1   },
  Bug:      { Normal:1, Fire:0.5, Water:1,   Grass:2,   Electric:1,   Ice:1,   Fighting:0.5, Poison:0.5, Ground:1,   Flying:0.5, Psychic:2,   Bug:1,   Rock:1,   Ghost:0.5, Dragon:1,   Dark:2,   Steel:0.5, Fairy:0.5 },
  Rock:     { Normal:1, Fire:2,   Water:1,   Grass:1,   Electric:1,   Ice:2,   Fighting:0.5, Poison:1,   Ground:0.5, Flying:2,   Psychic:1,   Bug:2,   Rock:1,   Ghost:1,   Dragon:1,   Dark:1,   Steel:0.5, Fairy:1   },
  Ghost:    { Normal:0, Fire:1,   Water:1,   Grass:1,   Electric:1,   Ice:1,   Fighting:0,   Poison:1,   Ground:1,   Flying:1,   Psychic:2,   Bug:1,   Rock:1,   Ghost:2,   Dragon:1,   Dark:0.5, Steel:1,   Fairy:1   },
  Dragon:   { Normal:1, Fire:1,   Water:1,   Grass:1,   Electric:1,   Ice:1,   Fighting:1,   Poison:1,   Ground:1,   Flying:1,   Psychic:1,   Bug:1,   Rock:1,   Ghost:1,   Dragon:2,   Dark:1,   Steel:0.5, Fairy:0   },
  Dark:     { Normal:1, Fire:1,   Water:1,   Grass:1,   Electric:1,   Ice:1,   Fighting:0.5, Poison:1,   Ground:1,   Flying:1,   Psychic:2,   Bug:1,   Rock:1,   Ghost:2,   Dragon:1,   Dark:0.5, Steel:0.5, Fairy:0.5 },
  Steel:    { Normal:1, Fire:0.5, Water:0.5, Grass:1,   Electric:0.5, Ice:2,   Fighting:1,   Poison:1,   Ground:1,   Flying:1,   Psychic:1,   Bug:1,   Rock:2,   Ghost:1,   Dragon:1,   Dark:1,   Steel:0.5, Fairy:2   },
  Fairy:    { Normal:1, Fire:0.5, Water:1,   Grass:1,   Electric:1,   Ice:1,   Fighting:2,   Poison:0.5, Ground:1,   Flying:1,   Psychic:1,   Bug:1,   Rock:1,   Ghost:1,   Dragon:2,   Dark:2,   Steel:0.5, Fairy:1   },
};

/**
 * Net effectiveness of an attacking type against a (possibly dual-type) defender.
 * Multiplies the multipliers for each defender type slot, correctly handling:
 *   - 4× weaknesses  (Golem Rock/Ground vs Grass = 2×2 = 4×)
 *   - Cancellations  (Gyarados Water/Flying vs Ice = 0.5×2 = 1× → NOT weak)
 *   - Immunities     (Gengar Ghost/Poison vs Normal = 0×1 = 0)
 */
export function netEffectiveness(attacker: PokemonType, defenderTypes: PokemonType[]): number {
  let mult = 1;
  for (const dt of defenderTypes) {
    mult *= TYPE_CHART[attacker][dt];
  }
  return mult;
}

/** Types that each attacking type hits super-effectively (2×) via STAB — for coverage display. */
export const SUPER_EFFECTIVE: Record<PokemonType, PokemonType[]> = {
  Normal:   [],
  Fire:     ["Grass", "Ice", "Bug", "Steel"],
  Water:    ["Fire", "Ground", "Rock"],
  Grass:    ["Water", "Ground", "Rock"],
  Electric: ["Water", "Flying"],
  Ice:      ["Grass", "Ground", "Flying", "Dragon"],
  Fighting: ["Normal", "Ice", "Rock", "Dark", "Steel"],
  Poison:   ["Grass", "Fairy"],
  Ground:   ["Fire", "Electric", "Poison", "Rock", "Steel"],
  Flying:   ["Grass", "Fighting", "Bug"],
  Psychic:  ["Fighting", "Poison"],
  Bug:      ["Grass", "Psychic", "Dark"],
  Rock:     ["Fire", "Ice", "Flying", "Bug"],
  Ghost:    ["Psychic", "Ghost"],
  Dragon:   ["Dragon"],
  Dark:     ["Psychic", "Ghost"],
  Steel:    ["Ice", "Rock", "Fairy"],
  Fairy:    ["Fighting", "Dragon", "Dark"],
};
