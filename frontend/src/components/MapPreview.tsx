import { MapContainer, TileLayer, Marker } from "react-leaflet";
import { useMap } from "react-leaflet";
import { useEffect, useRef } from "react";
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
 * Uses the standard Web Mercator formula:
 *   metersPerPixel = 156543.03 * cos(lat) / 2^zoom
 * We target ~600px map width as reference.
 */
function distanceToZoom(distMeters: number, latDeg: number): number {
  const latRad = (latDeg * Math.PI) / 180;
  const refPixels = 600;
  const metersPerPixel = (distMeters * 2) / refPixels;
  const zoom = Math.log2((156543.03 * Math.cos(latRad)) / metersPerPixel);
  return Math.max(1, Math.min(18, Math.round(zoom)));
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
 * Compute fitBounds corners from center, distance, and aspect ratio.
 */
function distanceToBounds(
  center: [number, number],
  distance: number,
  aspectRatio: number,
): L.LatLngBoundsExpression {
  const [lat, lon] = center;
  const latRad = (lat * Math.PI) / 180;
  const metersPerDegLat = 111320;
  const metersPerDegLon = 111320 * Math.cos(latRad);

  let halfLatDeg: number;
  let halfLonDeg: number;

  if (aspectRatio > 1) {
    // Wider than tall
    halfLonDeg = distance / metersPerDegLon;
    halfLatDeg = halfLonDeg / aspectRatio;
  } else {
    // Taller than wide
    halfLatDeg = distance / metersPerDegLat;
    halfLonDeg = halfLatDeg * aspectRatio;
  }

  return [
    [lat - halfLatDeg, lon - halfLonDeg],
    [lat + halfLatDeg, lon + halfLonDeg],
  ];
}

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
  const flyingRef = useRef(false);
  const skipZoomRef = useRef(false);

  useEffect(() => {
    flyingRef.current = true;
    skipZoomRef.current = true;
    map.flyTo(center, distanceToZoom(distance, center[0]), { duration: 1.5 });
    const timer = setTimeout(() => {
      flyingRef.current = false;
      skipZoomRef.current = false;
    }, 1600);
    return () => clearTimeout(timer);
  }, [center]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (flyingRef.current) return;
    skipZoomRef.current = true;

    const bounds = distanceToBounds(center, distance, aspectRatio);
    map.fitBounds(bounds, { padding: [40, 40], animate: true, duration: 0.3 });

    const timer = setTimeout(() => {
      skipZoomRef.current = false;
    }, 400);
    return () => clearTimeout(timer);
  }, [distance, aspectRatio]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    function onZoom() {
      if (skipZoomRef.current) return;
      const z = map.getZoom();
      const c = map.getCenter();
      onDistanceChange(zoomToDistance(z, c.lat));
    }
    map.on("zoomend", onZoom);
    return () => {
      map.off("zoomend", onZoom);
    };
  }, [map, onDistanceChange]);

  useEffect(() => {
    function onMove() {
      if (flyingRef.current) return;
      const c = map.getCenter();
      onCenterChange([c.lat, c.lng]);
    }
    map.on("moveend", onMove);
    return () => {
      map.off("moveend", onMove);
    };
  }, [map, onCenterChange]);

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
        <CanvasOverlay
          center={center}
          distance={distance}
          aspectRatio={aspectRatio}
          color={canvasColor}
        />
        {pinLocation && <Marker position={pinLocation} />}
      </MapContainer>
    </div>
  );
}
