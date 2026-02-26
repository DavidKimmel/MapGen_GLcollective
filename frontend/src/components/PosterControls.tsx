import { useState } from "react";
import type { PosterSettings } from "../types";
import { SIZE_PRESETS } from "../types";
import CropSelector from "./CropSelector";
import DetailToggle from "./DetailToggle";
import "./PosterControls.css";

interface Props {
  settings: PosterSettings;
  onChange: (s: PosterSettings) => void;
  showCrop?: boolean;
}

export default function PosterControls({ settings, onChange, showCrop = true }: Props) {
  const [activePreset, setActivePreset] = useState<string>('16\u00d720"');

  function set<K extends keyof PosterSettings>(key: K, val: PosterSettings[K]) {
    onChange({ ...settings, [key]: val });
  }

  function selectPreset(label: string, width: number, height: number) {
    setActivePreset(label);
    onChange({ ...settings, width, height });
  }

  return (
    <div className="poster-controls">
      <label>
        Distance: {(settings.distance / 1000).toFixed(1)} km
        <input
          type="range"
          min={2000}
          max={40000}
          step={500}
          value={settings.distance}
          onChange={(e) => set("distance", Number(e.target.value))}
        />
      </label>

      {showCrop && (
        <CropSelector
          value={settings.crop}
          onChange={(crop) => set("crop", crop)}
        />
      )}

      <DetailToggle
        enabled={settings.detail_layers}
        onChange={(v) => set("detail_layers", v)}
      />

      <div className="section-label">Print Size</div>
      <div className="size-presets">
        {SIZE_PRESETS.map((p) => (
          <button
            key={p.label}
            className={`preset-btn ${activePreset === p.label ? "active" : ""}`}
            onClick={() => selectPreset(p.label, p.width, p.height)}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="controls-row">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={settings.border}
            onChange={(e) => set("border", e.target.checked)}
          />
          Border
        </label>
      </div>
    </div>
  );
}
