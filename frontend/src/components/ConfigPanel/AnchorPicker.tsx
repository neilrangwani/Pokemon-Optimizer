/**
 * AnchorPicker.tsx — Select up to 5 anchor Pokémon that must appear on the team.
 *
 * The user types a Pokémon name, hits Enter or clicks Add.
 * Names are validated by the backend at optimization time.
 */

import { useState } from "react";
import { Tooltip } from "../shared/Tooltip";

const MAX_ANCHORS = 5;

interface Props {
  anchors: string[];
  onChange: (anchors: string[]) => void;
}

export function AnchorPicker({ anchors, onChange }: Props) {
  const [input, setInput] = useState("");

  const add = () => {
    const name = input.trim().toLowerCase().replace(/\s+/g, "-");
    if (!name || anchors.includes(name) || anchors.length >= MAX_ANCHORS) return;
    onChange([...anchors, name]);
    setInput("");
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
          <p>Enter the Pokémon's name as it appears in-game (e.g. "charizard", "mr-mime").</p>
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
              {name}
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

      {/* Input */}
      {anchors.length < MAX_ANCHORS && (
        <div className="flex gap-1">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") add(); }}
            placeholder="e.g. charizard"
            className="flex-1 bg-[#0F0F20] border border-[#3A3A5E] rounded px-2 py-1 text-[11px] text-[#FAFAF2] placeholder-[#4A4A5A] focus:border-[#CC0000] focus:outline-none font-['JetBrains_Mono']"
          />
          <button
            onClick={add}
            disabled={!input.trim()}
            className="px-2 py-1 rounded text-[10px] font-bold bg-[#2A2A3E] border border-[#3A3A5E] text-[#9090B0] hover:border-[#CC0000] hover:text-[#CC0000] disabled:opacity-40 transition-colors"
          >
            Add
          </button>
        </div>
      )}

      {anchors.length >= MAX_ANCHORS && (
        <p className="text-[10px] text-[#9090B0]">Max {MAX_ANCHORS} anchors reached.</p>
      )}
    </div>
  );
}
