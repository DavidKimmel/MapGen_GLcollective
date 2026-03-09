import type { Theme } from "../types";
import "./ThemeSelector.css";

interface Props {
  themes: Theme[];
  selected: string;
  onSelect: (id: string) => void;
}

const PRIORITY_ORDER = [
  "37th_parallel",
  "clay_sage",
  "vintage",
  "terracotta",
];

function sortThemes(themes: Theme[]): Theme[] {
  const priorityIndex = new Map(PRIORITY_ORDER.map((id, i) => [id, i]));
  return [...themes].sort((a, b) => {
    const ai = priorityIndex.get(a.id) ?? PRIORITY_ORDER.length;
    const bi = priorityIndex.get(b.id) ?? PRIORITY_ORDER.length;
    if (ai !== bi) return ai - bi;
    return a.name.localeCompare(b.name);
  });
}

export default function ThemeSelector({ themes, selected, onSelect }: Props) {
  const sorted = sortThemes(themes);

  return (
    <div className="theme-selector">
      <label htmlFor="theme-select">Theme</label>
      <select
        id="theme-select"
        className="theme-dropdown"
        value={selected}
        onChange={(e) => onSelect(e.target.value)}
      >
        {sorted.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
      </select>
    </div>
  );
}
