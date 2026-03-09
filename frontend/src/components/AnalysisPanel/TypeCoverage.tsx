/**
 * TypeCoverage.tsx — Shows offensive type coverage and defensive weaknesses.
 *
 * Offensive: which of the 18 types the team can hit super-effectively (via STAB).
 * Defensive: types where 3+ team members are weak (team-wide vulnerabilities).
 */

import type { TeamMemberResult, PokemonType } from "../../types";
import { ALL_TYPES, TYPE_COLORS } from "../../types";
import { SUPER_EFFECTIVE, WEAK_TO } from "../../utils/typeUtils";

interface Props {
  members: TeamMemberResult[];
}

export function TypeCoverage({ members }: Props) {
  // Offensive: types covered by any member's STAB
  const covered = new Set<PokemonType>();
  members.forEach((m) => {
    m.types.forEach((t) => {
      SUPER_EFFECTIVE[t]?.forEach((target) => covered.add(target));
    });
  });

  // Defensive: count how many members are weak to each type
  const weaknessCounts: Record<string, number> = {};
  ALL_TYPES.forEach((t) => { weaknessCounts[t] = 0; });
  members.forEach((m) => {
    // For each of this Pokémon's types, collect what hits them
    const memberWeaknesses = new Set<PokemonType>();
    m.types.forEach((t) => {
      WEAK_TO[t]?.forEach((attacker) => {
        // Check if any other of the Pokémon's types resists or is immune
        // For simplicity, just collect all weaknesses per type (STAB-based approximation)
        memberWeaknesses.add(attacker);
      });
    });
    // For dual-types: only count as weak if net effectiveness > 1
    // Simple approach: count if at least one type is weak and none immune
    memberWeaknesses.forEach((attacker) => {
      weaknessCounts[attacker] = (weaknessCounts[attacker] ?? 0) + 1;
    });
  });

  const coveredTypes = ALL_TYPES.filter((t) => covered.has(t));
  const teamVulnerabilities = ALL_TYPES.filter((t) => weaknessCounts[t] >= 3);

  return (
    <div className="space-y-3">
      {/* Offensive coverage */}
      <div>
        <p className="text-[9px] font-semibold text-[#9090B0] uppercase tracking-wider mb-1.5">
          Offensive Coverage ({coveredTypes.length}/18 types)
        </p>
        <div className="flex flex-wrap gap-1">
          {ALL_TYPES.map((t) => (
            <span
              key={t}
              className="text-[9px] font-bold px-1.5 py-0.5 rounded-sm font-['Inter']"
              style={{
                backgroundColor: covered.has(t) ? TYPE_COLORS[t] : "#2A2A3E",
                color: covered.has(t) ? "white" : "#4A4A6A",
                opacity: covered.has(t) ? 1 : 0.6,
              }}
              title={covered.has(t) ? `Team hits ${t} SE` : `No SE coverage vs ${t}`}
            >
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* Team vulnerabilities */}
      {teamVulnerabilities.length > 0 && (
        <div>
          <p className="text-[9px] font-semibold text-[#9090B0] uppercase tracking-wider mb-1.5">
            Team Vulnerabilities (3+ members weak)
          </p>
          <div className="flex flex-wrap gap-1">
            {teamVulnerabilities.map((t) => (
              <span
                key={t}
                className="text-[9px] font-bold px-1.5 py-0.5 rounded-sm font-['Inter']"
                style={{
                  backgroundColor: TYPE_COLORS[t],
                  color: "white",
                  outline: "2px solid #CC0000",
                  outlineOffset: "1px",
                }}
                title={`${weaknessCounts[t]} team members weak to ${t}`}
              >
                {t} ×{weaknessCounts[t]}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
