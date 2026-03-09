import type { PokemonType } from "../types";

/** Types that each attacking type hits super-effectively (2×). */
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

/** Types each type is weak to (takes 2× damage from). */
export const WEAK_TO: Record<PokemonType, PokemonType[]> = {
  Normal:   ["Fighting"],
  Fire:     ["Water", "Ground", "Rock"],
  Water:    ["Grass", "Electric"],
  Grass:    ["Fire", "Ice", "Poison", "Flying", "Bug"],
  Electric: ["Ground"],
  Ice:      ["Fire", "Fighting", "Rock", "Steel"],
  Fighting: ["Flying", "Psychic", "Fairy"],
  Poison:   ["Ground", "Psychic"],
  Ground:   ["Water", "Grass", "Ice"],
  Flying:   ["Electric", "Ice", "Rock"],
  Psychic:  ["Bug", "Ghost", "Dark"],
  Bug:      ["Fire", "Flying", "Rock"],
  Rock:     ["Water", "Grass", "Fighting", "Ground", "Steel"],
  Ghost:    ["Ghost", "Dark"],
  Dragon:   ["Ice", "Dragon", "Fairy"],
  Dark:     ["Fighting", "Bug", "Fairy"],
  Steel:    ["Fire", "Fighting", "Ground"],
  Fairy:    ["Poison", "Steel"],
};
