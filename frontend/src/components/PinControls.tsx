import { useState, useRef } from "react";
import { geocode } from "../api/client";
import "./PinControls.css";

interface Props {
  pinAddress: string;
  pinStyle: number;
  pinColor: string;
  onPinAddressChange: (v: string) => void;
  onPinStyleChange: (v: number) => void;
  onPinColorChange: (v: string) => void;
  onPinLocationChange: (lat: number | null, lon: number | null) => void;
  onCenterChange?: (lat: number, lon: number, displayName: string) => void;
}

const PIN_STYLES: { id: number; label: string; icon: string }[] = [
  { id: 1, label: "Heart", icon: "\u2665" },
  { id: 2, label: "Heart Pin", icon: "\u2764" },
  { id: 3, label: "Classic", icon: "\ud83d\udccd" },
  { id: 4, label: "House", icon: "\u2302" },
  { id: 5, label: "Grad Cap", icon: "\ud83c\udf93" },
];

type GeoStatus = "idle" | "locating" | "found" | "not_found";

export default function PinControls({
  pinAddress,
  pinStyle,
  pinColor,
  onPinAddressChange,
  onPinStyleChange,
  onPinColorChange,
  onPinLocationChange,
  onCenterChange,
}: Props) {
  const [geoStatus, setGeoStatus] = useState<GeoStatus>("idle");
  const [geoDisplay, setGeoDisplay] = useState("");
  const lastGeocoded = useRef("");

  async function doGeocode(address: string) {
    const trimmed = address.trim();
    if (!trimmed) {
      onPinLocationChange(null, null);
      setGeoStatus("idle");
      setGeoDisplay("");
      lastGeocoded.current = "";
      return;
    }
    if (trimmed === lastGeocoded.current) return;

    setGeoStatus("locating");
    try {
      const results = await geocode(trimmed);
      if (results.length > 0) {
        const r = results[0];
        onPinLocationChange(r.lat, r.lon);
        onCenterChange?.(r.lat, r.lon, r.display_name);
        setGeoStatus("found");
        setGeoDisplay(r.display_name);
        lastGeocoded.current = trimmed;
      } else {
        onPinLocationChange(null, null);
        setGeoStatus("not_found");
        setGeoDisplay("");
      }
    } catch {
      onPinLocationChange(null, null);
      setGeoStatus("not_found");
      setGeoDisplay("");
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      doGeocode(pinAddress);
    }
  }

  function handleBlur() {
    doGeocode(pinAddress);
  }

  function handleChange(v: string) {
    onPinAddressChange(v);
    if (!v.trim()) {
      onPinLocationChange(null, null);
      setGeoStatus("idle");
      setGeoDisplay("");
      lastGeocoded.current = "";
    }
  }

  return (
    <div className="pin-controls">
      <label>Pin Marker</label>
      <input
        type="text"
        className="pin-address-input"
        value={pinAddress}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder="Address to pin (press Enter to locate)"
      />

      {geoStatus === "locating" && (
        <div className="pin-geo-status locating">Locating...</div>
      )}
      {geoStatus === "found" && geoDisplay && (
        <div className="pin-geo-status found">Found: {geoDisplay}</div>
      )}
      {geoStatus === "not_found" && (
        <div className="pin-geo-status not-found">Not found</div>
      )}

      {pinAddress && (
        <>
          <div className="pin-style-row">
            <span className="pin-style-label">Style</span>
            <div className="pin-style-options">
              {PIN_STYLES.map((p) => (
                <button
                  key={p.id}
                  className={`pin-style-btn ${pinStyle === p.id ? "active" : ""}`}
                  onClick={() => onPinStyleChange(p.id)}
                  title={p.label}
                >
                  {p.icon}
                </button>
              ))}
            </div>
          </div>
          <div className="pin-color-row">
            <span className="pin-color-label">Color</span>
            <input
              type="color"
              value={pinColor || "#D4736B"}
              onChange={(e) => onPinColorChange(e.target.value)}
            />
            <input
              type="text"
              className="pin-color-hex"
              value={pinColor}
              onChange={(e) => onPinColorChange(e.target.value)}
              placeholder="#D4736B"
            />
          </div>
        </>
      )}
    </div>
  );
}
