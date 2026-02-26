import type { MapMode } from "../types";
import "./ModeSelector.css";

interface Props {
  mode: MapMode;
  onChange: (mode: MapMode) => void;
}

export default function ModeSelector({ mode, onChange }: Props) {
  return (
    <div className="mode-selector">
      <button
        className={`mode-btn ${mode === "city" ? "active" : ""}`}
        onClick={() => onChange("city")}
      >
        City Map
      </button>
      <button
        className={`mode-btn ${mode === "custom" ? "active" : ""}`}
        onClick={() => onChange("custom")}
      >
        Custom Map
      </button>
    </div>
  );
}
