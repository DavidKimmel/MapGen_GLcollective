import { useState, useEffect, useCallback } from "react";
import CitySearch from "./components/CitySearch";
import MapPreview from "./components/MapPreview";
import ThemeSelector from "./components/ThemeSelector";
import PosterControls from "./components/PosterControls";
import PinControls from "./components/PinControls";
import TextEditor from "./components/TextEditor";
import DownloadPanel from "./components/DownloadPanel";
import ModeSelector from "./components/ModeSelector";
import PosterPreview from "./components/PosterPreview";
import { fetchThemes } from "./api/client";
import type { GeoResult, Theme, PosterSettings, MapMode } from "./types";

const DEFAULT_CENTER: [number, number] = [48.8566, 2.3522];

function formatCoordText(lat: number, lon: number): string {
  const latDir = lat >= 0 ? "N" : "S";
  const lonDir = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(4)} ${latDir}, ${Math.abs(lon).toFixed(4)} ${lonDir}`;
}

export default function App() {
  const [city, setCity] = useState<GeoResult | null>(null);
  const [center, setCenter] = useState<[number, number]>(DEFAULT_CENTER);
  const [themes, setThemes] = useState<Theme[]>([]);
  const [selectedTheme, setSelectedTheme] = useState("37th_parallel");
  const [displayCity, setDisplayCity] = useState("");
  const [displaySubtitle, setDisplaySubtitle] = useState("");
  const [mode, setMode] = useState<MapMode>("city");

  // Pin state (frontend geocoded)
  const [pinLocation, setPinLocation] = useState<[number, number] | null>(null);

  // Preview state
  const [previewJobId, setPreviewJobId] = useState<string | null>(null);
  const [previewOutputFile, setPreviewOutputFile] = useState<string | null>(null);

  const [settings, setSettings] = useState<PosterSettings>({
    distance: 18000,
    width: 16,
    height: 20,
    format: "png",
    border: false,
    crop: "full",
    detail_layers: true,
    pin_address: "",
    pin_lat: null,
    pin_lon: null,
    pin_style: 1,
    pin_color: "",
    font_preset: 1,
    text_line_1: "",
    text_line_2: "",
    text_line_3: "",
  });

  useEffect(() => {
    fetchThemes().then(setThemes);
  }, []);

  function handleCitySelect(result: GeoResult) {
    setCity(result);
    setCenter([result.lat, result.lon]);
    setDisplayCity(result.city);
    setDisplaySubtitle(result.country);
    setPreviewJobId(null);

    // Auto-set coordinate text in city mode
    if (mode === "city") {
      setSettings((prev) => ({
        ...prev,
        text_line_3: formatCoordText(result.lat, result.lon),
      }));
    }
  }

  function handleModeChange(newMode: MapMode) {
    setMode(newMode);
    // Full reset when switching modes
    setCity(null);
    setCenter(DEFAULT_CENTER);
    setDisplayCity("");
    setDisplaySubtitle("");
    setPinLocation(null);
    setPreviewJobId(null);
    setPreviewOutputFile(null);
    setSettings({
      distance: 18000,
      width: 16,
      height: 20,
      format: "png",
      border: false,
      crop: "full",
      detail_layers: true,
      pin_address: "",
      pin_lat: null,
      pin_lon: null,
      pin_style: 1,
      pin_color: "",
      font_preset: 1,
      text_line_1: "",
      text_line_2: "",
      text_line_3: "",
    });
  }

  const handleDistanceChange = useCallback((d: number) => {
    setSettings((prev) => ({ ...prev, distance: d }));
  }, []);

  const handleCenterChange = useCallback((c: [number, number]) => {
    setCenter(c);
  }, []);

  const handlePinCenterChange = useCallback(
    (lat: number, lon: number, displayName: string) => {
      setCenter([lat, lon]);
      setCity({ lat, lon, display_name: displayName, city: displayName, country: "" });
      setDisplayCity(displayName);
      setSettings((prev) => ({
        ...prev,
        text_line_3: formatCoordText(lat, lon),
      }));
    },
    [],
  );

  const handlePinLocationChange = useCallback(
    (lat: number | null, lon: number | null) => {
      if (lat !== null && lon !== null) {
        setPinLocation([lat, lon]);
      } else {
        setPinLocation(null);
      }
      setSettings((prev) => ({ ...prev, pin_lat: lat, pin_lon: lon }));
    },
    [],
  );

  function set<K extends keyof PosterSettings>(key: K, val: PosterSettings[K]) {
    setSettings((prev) => ({ ...prev, [key]: val }));
  }

  function handlePosterReady(jobId: string, outputFile: string | null) {
    setPreviewJobId(jobId);
    setPreviewOutputFile(outputFile);
  }

  const currentTheme = themes.find((t) => t.id === selectedTheme);
  const canvasColor = currentTheme?.text ?? "#333";
  const aspectRatio = settings.width / settings.height;
  const isCustom = mode === "custom";

  return (
    <div className="app">
      <div className="sidebar">
        <h1 className="logo">MapGen</h1>

        {!isCustom && (
          <CitySearch
            onSelect={handleCitySelect}
            displayCity={displayCity}
            displaySubtitle={displaySubtitle}
            onDisplayCityChange={setDisplayCity}
            onDisplaySubtitleChange={setDisplaySubtitle}
          />
        )}

        <ModeSelector mode={mode} onChange={handleModeChange} />

        <hr className="section-divider" />

        <ThemeSelector
          themes={themes}
          selected={selectedTheme}
          onSelect={setSelectedTheme}
        />

        <hr className="section-divider" />

        <PosterControls settings={settings} onChange={setSettings} showCrop={isCustom} />

        {isCustom && (
          <>
            <hr className="section-divider" />

            <PinControls
              pinAddress={settings.pin_address}
              pinStyle={settings.pin_style}
              pinColor={settings.pin_color}
              onPinAddressChange={(v) => set("pin_address", v)}
              onPinStyleChange={(v) => set("pin_style", v)}
              onPinColorChange={(v) => set("pin_color", v)}
              onPinLocationChange={handlePinLocationChange}
              onCenterChange={handlePinCenterChange}
            />
          </>
        )}

        <hr className="section-divider" />

        <TextEditor
          textLine1={settings.text_line_1}
          textLine2={settings.text_line_2}
          textLine3={settings.text_line_3}
          fontPreset={settings.font_preset}
          onTextLine1Change={(v) => set("text_line_1", v)}
          onTextLine2Change={(v) => set("text_line_2", v)}
          onTextLine3Change={(v) => set("text_line_3", v)}
          onFontPresetChange={(v) => set("font_preset", v)}
          showLine3={isCustom}
          showFontPreset={isCustom}
        />

        <hr className="section-divider" />

        <DownloadPanel
          city={city}
          center={center}
          theme={selectedTheme}
          settings={settings}
          displayCity={displayCity}
          displaySubtitle={displaySubtitle}
          pinLat={pinLocation ? pinLocation[0] : null}
          pinLon={pinLocation ? pinLocation[1] : null}
          onPosterReady={handlePosterReady}
        />
      </div>
      <div className="map-area">
        <div className="map-section">
          <MapPreview
            center={center}
            distance={settings.distance}
            aspectRatio={aspectRatio}
            canvasColor={canvasColor}
            pinLocation={pinLocation}
            onDistanceChange={handleDistanceChange}
            onCenterChange={handleCenterChange}
          />
        </div>
        <div className="preview-section">
          <PosterPreview
            jobId={previewJobId}
            outputFile={previewOutputFile}
          />
        </div>
      </div>
    </div>
  );
}
