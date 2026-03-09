/**
 * AnchorPicker.tsx — Select up to 5 anchor Pokémon that must appear on the team.
 *
 * As the user types, suggestions from the current eligible pool appear in a dropdown.
 * Clicking a suggestion (or pressing Enter) adds the Pokémon as an anchor.
 */

import { useState, useRef } from "react";
import { Tooltip } from "../shared/Tooltip";

const MAX_ANCHORS = 5;

interface Candidate {
  name: string;         // slug used by backend (e.g. "charizard")
  display_name: string; // display name (e.g. "Charizard")
}

interface Props {
  anchors: string[];
  candidates: Candidate[];
  onChange: (anchors: string[]) => void;
}

export function AnchorPicker({ anchors, candidates, onChange }: Props) {
  const [input, setInput] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const query = input.trim().toLowerCase().replace(/\s+/g, "-");

  const suggestions = query.length >= 1
    ? candidates
        .filter(
          (c) =>
            !anchors.includes(c.name) &&
            (c.display_name.toLowerCase().replace(/\s+/g, "-").startsWith(query) ||
              c.name.startsWith(query))
        )
        .slice(0, 8)
    : [];

  const add = (name: string) => {
    if (!name || anchors.includes(name) || anchors.length >= MAX_ANCHORS) return;
    onChange([...anchors, name]);
    setInput("");
    setShowDropdown(false);
  };

  const addFromInput = () => {
    if (suggestions.length > 0) {
      add(suggestions[0].name);
    } else if (query) {
      add(query);
    }
  };

  const remove = (name: string) => {
    onChange(anchors.filter((a) => a !== name));
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-[#FAFAF2] uppercase tracking-wider">
          Anchor Pokémon
        </span>
        <Tooltip title="Anchor Pokémon">
          <p className="mb-1.5">Lock up to 5 Pokémon that <strong>must</strong> appear on the optimized team.</p>
          <p className="mb-1.5">The ILP solver adds a hard constraint <code>x_i = 1</code> for each anchor.</p>
          <p>Type a name and select from the dropdown, or press Enter to add.</p>
        </Tooltip>
      </div>

      {/* Chips */}
      {anchors.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {anchors.map((name) => (
            <span
              key={name}
              className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#CC0000] text-white"
            >
              {candidates.find((c) => c.name === name)?.display_name ?? name}
              <button
                onClick={() => remove(name)}
                className="hover:opacity-70 transition-opacity leading-none"
                aria-label={`Remove ${name}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Input + dropdown */}
      {anchors.length < MAX_ANCHORS && (
        <div className="relative">
          <div className="flex gap-1">
            <input
              type="text"
              value={input}
              onChange={(e) => { setInput(e.target.value); setShowDropdown(true); }}
              onKeyDown={(e) => { if (e.key === "Enter") addFromInput(); if (e.key === "Escape") setShowDropdown(false); }}
              onFocus={() => setShowDropdown(true)}
              onBlur={() => { blurTimer.current = setTimeout(() => setShowDropdown(false), 150); }}
              placeholder="search Pokémon…"
              className="flex-1 bg-[#0F0F20] border border-[#3A3A5E] rounded px-2 py-1 text-[11px] text-[#FAFAF2] placeholder-[#4A4A5A] focus:border-[#CC0000] focus:outline-none font-['JetBrains_Mono']"
            />
            <button
              onClick={addFromInput}
              disabled={!query}
              className="px-2 py-1 rounded text-[10px] font-bold bg-[#2A2A3E] border border-[#3A3A5E] text-[#9090B0] hover:border-[#CC0000] hover:text-[#CC0000] disabled:opacity-40 transition-colors"
            >
              Add
            </button>
          </div>

          {showDropdown && suggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-0.5 bg-[#1A1A2E] border border-[#3A3A5E] rounded shadow-lg z-50 overflow-hidden">
              {suggestions.map((c) => (
                <button
                  key={c.name}
                  onMouseDown={(e) => {
                    e.preventDefault(); // prevent input blur before click
                    if (blurTimer.current) clearTimeout(blurTimer.current);
                    add(c.name);
                  }}
                  className="w-full text-left px-3 py-1.5 text-[11px] text-[#DADAE8] hover:bg-[#CC0000] hover:text-white transition-colors font-['Inter']"
                >
                  {c.display_name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {anchors.length >= MAX_ANCHORS && (
        <p className="text-[10px] text-[#9090B0]">Max {MAX_ANCHORS} anchors reached.</p>
      )}
    </div>
  );
}
