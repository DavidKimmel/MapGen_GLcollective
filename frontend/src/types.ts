export interface GeoResult {
  display_name: string;
  lat: number;
  lon: number;
  city: string;
  country: string;
}

export interface Theme {
  id: string;
  name: string;
  description?: string;
  bg: string;
  text: string;
  gradient_color: string;
  water: string;
  parks: string;
  road_motorway: string;
  road_primary: string;
  road_secondary: string;
  road_tertiary: string;
  road_residential: string;
  road_default: string;
}

export interface JobStatus {
  status: "processing" | "complete" | "error";
  output_file: string | null;
  error: string | null;
}

export interface SizePreset {
  label: string;
  width: number;
  height: number;
}

export const SIZE_PRESETS: SizePreset[] = [
  { label: '8\u00d710"', width: 8, height: 10 },
  { label: '11\u00d714"', width: 11, height: 14 },
  { label: '16\u00d720"', width: 16, height: 20 },
  { label: '18\u00d724"', width: 18, height: 24 },
  { label: '24\u00d736"', width: 24, height: 36 },
];

export type CropShape = "full" | "circle" | "heart" | "house";

export type MapMode = "city" | "custom";

export interface PosterSettings {
  distance: number;
  width: number;
  height: number;
  format: "png";
  border: boolean;
  crop: CropShape;
  detail_layers: boolean;
  pin_address: string;
  pin_lat: number | null;
  pin_lon: number | null;
  pin_style: number;
  pin_color: string;
  font_preset: number;
  text_line_1: string;
  text_line_2: string;
  text_line_3: string;
  map_only: boolean;
}
