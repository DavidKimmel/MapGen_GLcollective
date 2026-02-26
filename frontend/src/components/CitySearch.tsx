import { useState, useEffect, useRef } from "react";
import { useDebounce } from "../hooks/useDebounce";
import { geocode } from "../api/client";
import type { GeoResult } from "../types";
import "./CitySearch.css";

interface Props {
  onSelect: (result: GeoResult) => void;
  displayCity: string;
  displaySubtitle: string;
  onDisplayCityChange: (v: string) => void;
  onDisplaySubtitleChange: (v: string) => void;
}

export default function CitySearch({
  onSelect,
  displayCity,
  displaySubtitle,
  onDisplayCityChange,
  onDisplaySubtitleChange,
}: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GeoResult[]>([]);
  const [open, setOpen] = useState(false);
  const debounced = useDebounce(query, 400);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (debounced.length < 2) {
      setResults([]);
      return;
    }
    let cancelled = false;
    geocode(debounced).then((r) => {
      if (!cancelled) {
        setResults(r);
        setOpen(r.length > 0);
      }
    });
    return () => { cancelled = true; };
  }, [debounced]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function pick(r: GeoResult) {
    setQuery(r.city);
    setOpen(false);
    onSelect(r);
  }

  return (
    <div className="city-search" ref={wrapperRef}>
      <label>Search City</label>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="e.g. Paris, London, Tokyo..."
      />
      {open && (
        <ul className="city-search-dropdown">
          {results.map((r, i) => (
            <li key={i} onClick={() => pick(r)}>
              {r.display_name}
            </li>
          ))}
        </ul>
      )}

      {displayCity && (
        <div className="display-name-fields">
          <label>
            Display Name
            <input
              type="text"
              value={displayCity}
              onChange={(e) => onDisplayCityChange(e.target.value)}
            />
          </label>
          <label>
            Subtitle
            <input
              type="text"
              value={displaySubtitle}
              onChange={(e) => onDisplaySubtitleChange(e.target.value)}
            />
          </label>
        </div>
      )}
    </div>
  );
}
