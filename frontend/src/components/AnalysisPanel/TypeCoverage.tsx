/**
 * TypeCoverage.tsx — Shows offensive type coverage and defensive weaknesses.
 *
 * Offensive: which of the 18 types the team can hit super-effectively (via STAB).
 *   Clicking a covered type badge cycles through the Pokémon that provide that coverage.
 * Defensive: types where 3+ team members have net weakness (>1× multiplier).
 *   Uses the full 18×18 chart with proper dual-type multiplier math, so cancellations
 *   (e.g. Gyarados Water/Flying vs Ice = 0.5×2 = 1× → not weak) are handled correctly.
 */

import type { TeamMemberResult, PokemonType } from "../../types";
import { ALL_TYPES, TYPE_COLORS } from "../../types";
import { SUPER_EFFECTIVE, netEffectiveness } from "../../utils/typeUtils";

interface Props {
  members: TeamMemberResult[];
  selectedMember: string | null;
  highlightedMembers: string[];
  onSelectMember: (name: string | null) => void;
  onHighlightMembers: (names: string[]) => void;
}

export function TypeCoverage({ members, selectedMember, highlightedMembers, onSelectMember, onHighlightMembers }: Props) {
  // Offensive: types covered by any member's STAB; track which members cover each type
  const covered = new Set<PokemonType>();
  const coveringMembers: Record<string, string[]> = {};

  members.forEach((m) => {
    m.types.forEach((t) => {
      SUPER_EFFECTIVE[t as PokemonType]?.forEach((target) => {
        covered.add(target);
        if (!coveringMembers[target]) coveringMembers[target] = [];
        if (!coveringMembers[target].includes(m.name)) coveringMembers[target].push(m.name);
      });
    });
  });

  // Defensive: count members with net weakness using full type chart multiplication.
  // This correctly handles dual-type interactions — 4× still counts as 1 Pokémon,
  // and cancelled weaknesses (e.g. Water resists Ice on Gyarados) are NOT counted.
  const weaknessCounts: Record<string, number> = {};
  ALL_TYPES.forEach((t) => { weaknessCounts[t] = 0; });
  members.forEach((m) => {
    ALL_TYPES.forEach((attacker) => {
      const eff = netEffectiveness(attacker as PokemonType, m.types as PokemonType[]);
      if (eff > 1.0) weaknessCounts[attacker] = (weaknessCounts[attacker] ?? 0) + 1;
    });
  });

  const coveredTypes = ALL_TYPES.filter((t) => covered.has(t as PokemonType));
  const teamVulnerabilities = ALL_TYPES.filter((t) => weaknessCounts[t] >= 3);

  // Pre-compute which members are vulnerable to each type (for vulnerability click)
  const vulnerableMembers: Record<string, string[]> = {};
  teamVulnerabilities.forEach((t) => {
    vulnerableMembers[t] = members
      .filter((m) => netEffectiveness(t as PokemonType, m.types as PokemonType[]) > 1.0)
      .map((m) => m.name);
  });

  const handleVulnerabilityClick = (t: PokemonType) => {
    const targets = vulnerableMembers[t] ?? [];
    if (targets.length === 0) return;
    // If all vulnerable members are already highlighted, toggle off; otherwise highlight all.
    const allHighlighted = targets.every((name) => highlightedMembers.includes(name));
    onHighlightMembers(allHighlighted ? [] : targets);
  };

  const handleTypeClick = (t: PokemonType) => {
    const providers = coveringMembers[t] ?? [];
    if (providers.length === 0) return;
    // Cycle through providers; clicking the same single provider again deselects.
    const currentIdx = providers.indexOf(selectedMember ?? "");
    if (providers.length === 1) {
      onSelectMember(currentIdx === 0 ? null : providers[0]);
    } else {
      onSelectMember(providers[(currentIdx + 1) % providers.length]);
    }
  };

  return (
    <div className="space-y-3">
      {/* Offensive coverage */}
      <div>
        <p className="text-[9px] font-semibold text-[#9090B0] uppercase tracking-wider mb-1.5">
          Offensive Coverage ({coveredTypes.length}/18 types)
        </p>
        <div className="flex flex-wrap gap-1">
          {ALL_TYPES.map((t) => {
            const isCovered = covered.has(t as PokemonType);
            const providers = coveringMembers[t] ?? [];
            const isProviderSelected = providers.includes(selectedMember ?? "");
            return (
              <span
                key={t}
                onClick={() => isCovered && handleTypeClick(t as PokemonType)}
                className="text-[9px] font-bold px-1.5 py-0.5 rounded-sm font-['Inter'] transition-all"
                style={{
                  backgroundColor: isCovered ? TYPE_COLORS[t as PokemonType] : "#2A2A3E",
                  color: isCovered ? "white" : "#4A4A6A",
                  opacity: isCovered ? 1 : 0.6,
                  cursor: isCovered ? "pointer" : "default",
                  outline: isProviderSelected ? "2px solid white" : "none",
                  outlineOffset: "1px",
                }}
                title={
                  isCovered
                    ? `${providers.join(", ")} — click to highlight`
                    : `No SE coverage vs ${t}`
                }
              >
                {t}
              </span>
            );
          })}
        </div>
      </div>

      {/* Team vulnerabilities */}
      {teamVulnerabilities.length > 0 && (
        <div>
          <p className="text-[9px] font-semibold text-[#9090B0] uppercase tracking-wider mb-1.5">
            Team Vulnerabilities (3+ members weak)
          </p>
          <div className="flex flex-wrap gap-1">
            {teamVulnerabilities.map((t) => {
              const targets = vulnerableMembers[t] ?? [];
              const isVulnerableSelected = targets.length > 0 && targets.every((n) => highlightedMembers.includes(n));
              return (
                <span
                  key={t}
                  onClick={() => handleVulnerabilityClick(t as PokemonType)}
                  className="text-[9px] font-bold px-1.5 py-0.5 rounded-sm font-['Inter'] transition-all"
                  style={{
                    backgroundColor: TYPE_COLORS[t as PokemonType],
                    color: "white",
                    outline: isVulnerableSelected ? "2px solid white" : "2px solid #CC0000",
                    outlineOffset: "1px",
                    cursor: "pointer",
                  }}
                  title={`${targets.join(", ")} weak to ${t} — click to highlight`}
                >
                  {t} ×{weaknessCounts[t]}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
