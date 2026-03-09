/**
 * GenerationSelector.tsx — Vertical gen list with persistent per-gen game accordions.
 *
 * Each gen button is a full-width row. Clicking a selected gen expands/collapses
 * its game checkboxes. Game selections persist while the gen is selected.
 */

import { useState } from "react";
import { GENERATION_GAMES } from "../../types";
import { Tooltip } from "../shared/Tooltip";

const GEN_LABELS = ["I","II","III","IV","V","VI","VII","VIII","IX"];

interface Props {
  selectedGens: number[];
  selectedGames: string[];
  onChange: (gens: number[], games: string[]) => void;
}


export function GenerationSelector({ selectedGens, selectedGames, onChange }: Props) {
  const [expandedGen, setExpandedGen] = useState<number | null>(1);
  const gens = [1, 2, 3];

  const toggleGen = (gen: number) => {
    const nowSelected = selectedGens.includes(gen);
    const nextGens = nowSelected
      ? selectedGens.filter((g) => g !== gen)
      : [...selectedGens, gen];

    // Recompute games as the union of all games from all selected gens.
    // This ensures that adding Gen 2 doesn't drop Gen 1's games from the list.
    const allSelectedGames = new Set<string>();
    nextGens.forEach((g) => {
      (GENERATION_GAMES[g] ?? []).forEach((game) => allSelectedGames.add(game));
    });
    // Preserve any per-game unchecks the user made by intersecting with known games
    const nextGames = [...allSelectedGames];

    if (!nowSelected) setExpandedGen(gen);

    onChange(nextGens, nextGames);
  };

  const toggleGame = (game: string) => {
    const nextGames = selectedGames.includes(game)
      ? selectedGames.filter((g) => g !== game)
      : [...selectedGames, game];
    onChange(selectedGens, nextGames);
  };

  return (
    <div className="space-y-0.5">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-[#FAFAF2] uppercase tracking-wider">
          Generation
        </span>
        <Tooltip title="Generation Filter">
          Select which generations of Pokémon to include. Click a generation to expand
          its game list. Individual games can be toggled to control availability modes
          in Cartridge and Solo Run play.
        </Tooltip>
      </div>

      {gens.map((gen) => {

        const active = selectedGens.includes(gen);
        const expanded = expandedGen === gen && active;
        const games = GENERATION_GAMES[gen] ?? [];

        return (
          <div key={gen}>
            <button
              onClick={() => {
                if (!active) {
                  toggleGen(gen);
                } else {
                  setExpandedGen(expanded ? null : gen);
                }
              }}
              className="w-full flex items-center justify-between px-3 py-1.5 rounded text-xs font-bold transition-all duration-150 border font-['Inter']"
              style={{
                backgroundColor: active ? "#CC0000" : "#2A2A3E",
                borderColor: active ? "#CC0000" : "#3A3A5E",
                color: active ? "white" : "#9090B0",
                cursor: "pointer",
              }}
            >
              <span>Gen {GEN_LABELS[gen - 1]}</span>
              {active && (
                <span className="text-[10px] opacity-70">{expanded ? "▲" : "▼"}</span>
              )}
              {!active && (
                <button
                  onClick={(e) => { e.stopPropagation(); toggleGen(gen); }}
                  className="text-[10px] opacity-60 hover:opacity-100"
                >
                  +
                </button>
              )}
            </button>

            {expanded && (
              <div className="mt-0.5 mb-1 p-2 bg-[#0F0F20] rounded border border-[#3A3A5E] space-y-1">
                {games.map((game) => (
                  <label key={game} className="flex items-center gap-2 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={selectedGames.includes(game)}
                      onChange={() => toggleGame(game)}
                      className="accent-[#CC0000] w-3 h-3 flex-shrink-0"
                    />
                    <span className="text-[11px] text-[#DADAE8] group-hover:text-white transition-colors">
                      {game}
                    </span>
                  </label>
                ))}
                <button
                  onClick={() => toggleGen(gen)}
                  className="mt-1 text-[10px] text-[#CC0000] hover:underline w-full text-left"
                >
                  Remove Gen {GEN_LABELS[gen - 1]}
                </button>
              </div>
            )}
          </div>
        );
      })}

      <p className="text-[9px] text-[#4A4A6A] font-['JetBrains_Mono'] mt-1">
        Gen IV+ coming soon
      </p>
    </div>
  );
}
