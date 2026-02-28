import { MapContainer, TileLayer, Marker } from "react-leaflet";
import { useMap } from "react-leaflet";
import { useEffect, useRef, useCallback } from "react";
import L from "leaflet";
import CanvasOverlay from "./CanvasOverlay";
import "./MapPreview.css";

interface Props {
  center: [number, number];
  distance: number;
  aspectRatio: number;
  canvasColor: string;
  pinLocation: [number, number] | null;
  onDistanceChange: (d: number) => void;
  onCenterChange: (c: [number, number]) => void;
}

/**
 * Convert distance (meters) to approximate Leaflet zoom level.
 * Uses the standard Web Mercator formula.
 */
function distanceToZoom(distMeters: number, latDeg: number): number {
  const latRad = (latDeg * Math.PI) / 180;
  const refPixels = 600;
  const metersPerPixel = (distMeters * 2) / refPixels;
  const zoom = Math.log2((156543.03 * Math.cos(latRad)) / metersPerPixel);
  return Math.max(1, Math.min(18, zoom)); // no rounding — allow fractional zoom
}

/**
 * Convert Leaflet zoom level back to distance (meters).
 */
function zoomToDistance(zoom: number, latDeg: number): number {
  const latRad = (latDeg * Math.PI) / 180;
  const refPixels = 600;
  const metersPerPixel = (156543.03 * Math.cos(latRad)) / Math.pow(2, zoom);
  return Math.round((metersPerPixel * refPixels) / 2);
}

/**
 * MapSync handles programmatic view changes and relays user interactions
 * back to React state. The key principle: only animate the map when the
 * center changes from an external source (city search, pin placement),
 * never in response to the user's own panning.
 */
function MapSync({
  center,
  distance,
  aspectRatio,
  onDistanceChange,
  onCenterChange,
}: {
  center: [number, number];
  distance: number;
  aspectRatio: number;
  onDistanceChange: (d: number) => void;
  onCenterChange: (c: [number, number]) => void;
}) {
  const map = useMap();
  const programmaticRef = useRef(false);
  const prevCenterRef = useRef<[number, number]>(center);

  // Fly to new center only when it genuinely changes from an external source
  // (city search, pin geocode) — detected by comparing against previous value.
  useEffect(() => {
    const [prevLat, prevLon] = prevCenterRef.current;
    const [newLat, newLon] = center;

    // Skip if coordinates haven't meaningfully changed (from user's own pan)
    if (Math.abs(prevLat - newLat) < 0.0001 && Math.abs(prevLon - newLon) < 0.0001) {
      return;
    }

    prevCenterRef.current = center;
    programmaticRef.current = true;
    map.flyTo(center, distanceToZoom(distance, center[0]), { duration: 1.2 });

    const timer = setTimeout(() => {
      programmaticRef.current = false;
    }, 1300);
    return () => clearTimeout(timer);
  }, [center]); // eslint-disable-line react-hooks/exhaustive-deps

  // Adjust view when distance or aspect ratio changes (from slider/size picker)
  useEffect(() => {
    if (programmaticRef.current) return;
    programmaticRef.current = true;

    const zoom = distanceToZoom(distance, center[0]);
    map.setZoom(zoom, { animate: true });

    const timer = setTimeout(() => {
      programmaticRef.current = false;
    }, 400);
    return () => clearTimeout(timer);
  }, [distance, aspectRatio]); // eslint-disable-line react-hooks/exhaustive-deps

  // Relay user panning back to React state
  const onMoveEnd = useCallback(() => {
    if (programmaticRef.current) return;
    const c = map.getCenter();
    prevCenterRef.current = [c.lat, c.lng];
    onCenterChange([c.lat, c.lng]);
  }, [map, onCenterChange]);

  // Relay user zooming back to distance state
  const onZoomEnd = useCallback(() => {
    if (programmaticRef.current) return;
    const z = map.getZoom();
    const c = map.getCenter();
    onDistanceChange(zoomToDistance(z, c.lat));
  }, [map, onDistanceChange]);

  useEffect(() => {
    map.on("moveend", onMoveEnd);
    map.on("zoomend", onZoomEnd);
    return () => {
      map.off("moveend", onMoveEnd);
      map.off("zoomend", onZoomEnd);
    };
  }, [map, onMoveEnd, onZoomEnd]);

  return null;
}

export default function MapPreview({
  center,
  distance,
  aspectRatio,
  canvasColor,
  pinLocation,
  onDistanceChange,
  onCenterChange,
}: Props) {
  return (
    <div className="map-preview">
      <MapContainer
        center={center}
        zoom={distanceToZoom(distance, center[0])}
        style={{ width: "100%", height: "100%" }}
        zoomControl={true}
        zoomSnap={0}
        zoomDelta={0.5}
        wheelPxPerZoomLevel={120}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapSync
          center={center}
          distance={distance}
          aspectRatio={aspectRatio}
          onDistanceChange={onDistanceChange}
          onCenterChange={onCenterChange}
        />
        {pinLocation && <Marker position={pinLocation} />}
      </MapContainer>
      <CanvasOverlay aspectRatio={aspectRatio} color={canvasColor} />
    </div>
  );
}
