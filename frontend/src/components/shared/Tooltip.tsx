/**
 * Tooltip.tsx — Portal-based ? bubble tooltip.
 *
 * Uses ReactDOM.createPortal to escape any overflow:hidden/auto parent container.
 * Measures button position via getBoundingClientRect and renders fixed above the button.
 */

import { useRef, useState, useEffect } from "react";
import { createPortal } from "react-dom";

interface TooltipProps {
  title: string;
  children: React.ReactNode;
}

export function Tooltip({ title, children }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0, above: true });
  const btnRef = useRef<HTMLButtonElement>(null);

  const toggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!open && btnRef.current) {
      const r = btnRef.current.getBoundingClientRect();
      const above = r.top > 290;
      setCoords({
        top: above ? r.top : r.bottom,
        left: r.left + r.width / 2,
        above,
      });
    }
    setOpen((v) => !v);
  };

  // Close on any outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (btnRef.current && !btnRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <span className="relative inline-flex items-center">
      <button
        ref={btnRef}
        onClick={toggle}
        className="w-4 h-4 rounded-full text-[9px] font-bold border border-[#CC0000] text-[#CC0000] hover:bg-[#CC0000] hover:text-white transition-colors flex items-center justify-center flex-shrink-0"
        aria-label={`Help: ${title}`}
      >
        ?
      </button>

      {open &&
        createPortal(
          <div
            style={{
              position: "fixed",
              top: coords.top,
              left: Math.max(148, Math.min(coords.left, window.innerWidth - 148)),
              transform: coords.above
                ? "translate(-50%, calc(-100% - 8px))"
                : "translate(-50%, 8px)",
              zIndex: 9999,
            }}
            className="w-72 rounded shadow-xl border border-[#E8E8D8] overflow-hidden"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="bg-[#CC0000] px-3 py-2">
              <span className="text-white text-xs font-semibold font-['Inter']">
                {title}
              </span>
            </div>
            <div className="bg-[#FAFAF2] px-3 py-3 text-xs text-[#4A4A5A] leading-relaxed font-['Inter']">
              {children}
            </div>
          </div>,
          document.body
        )}
    </span>
  );
}
