import { useMap } from "react-leaflet";
import { useEffect } from "react";
import L from "leaflet";

interface Props {
  center: [number, number];
  distance: number;
  aspectRatio: number;
  color: string;
}

export default function CanvasOverlay({ center, distance, aspectRatio, color }: Props) {
  const map = useMap();

  useEffect(() => {
    const [lat, lon] = center;

    const maxDim = Math.max(aspectRatio, 1);
    const minDim = Math.min(aspectRatio, 1);
    const compensatedDist = distance * (maxDim / minDim) / 4;

    const latDeg = compensatedDist / 111_320;
    const lonDeg = compensatedDist / (111_320 * Math.cos((lat * Math.PI) / 180));

    let halfLat: number, halfLon: number;
    if (aspectRatio > 1) {
      halfLon = lonDeg;
      halfLat = lonDeg / aspectRatio;
    } else {
      halfLat = latDeg;
      halfLon = latDeg * aspectRatio;
    }

    const bounds: L.LatLngBoundsExpression = [
      [lat - halfLat, lon - halfLon],
      [lat + halfLat, lon + halfLon],
    ];

    const rect = L.rectangle(bounds, {
      color,
      weight: 2,
      dashArray: "8 4",
      fill: false,
    }).addTo(map);

    return () => {
      map.removeLayer(rect);
    };
  }, [map, center, distance, aspectRatio, color]);

  return null;
}
