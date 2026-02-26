import type { Theme } from "../types";
import "./ThemeSelector.css";

interface Props {
  themes: Theme[];
  selected: string;
  onSelect: (id: string) => void;
}

const SWATCH_KEYS: (keyof Theme)[] = [
  "bg", "text", "water", "parks", "road_motorway", "road_primary",
];

export default function ThemeSelector({ themes, selected, onSelect }: Props) {
  return (
    <div className="theme-selector">
      <label>Theme</label>
      <div className="theme-grid">
        {themes.map((t) => (
          <div
            key={t.id}
            className={`theme-card ${t.id === selected ? "selected" : ""}`}
            onClick={() => onSelect(t.id)}
          >
            <div className="theme-swatches">
              {SWATCH_KEYS.map((k) => (
                <span
                  key={k}
                  className="swatch"
                  style={{ background: t[k] as string }}
                />
              ))}
            </div>
            <span className="theme-name">{t.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
