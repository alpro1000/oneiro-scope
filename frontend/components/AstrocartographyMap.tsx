'use client';

import 'leaflet/dist/leaflet.css';
import { useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, CircleMarker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import type { AcgLineFeature } from '../lib/astrocartography-client';

const PLANET_COLOR: Record<string, string> = {
  sun: '#f2a900',
  moon: '#5b8def',
  mercury: '#8a4fc4',
  venus: '#e8559a',
  mars: '#d23b2e',
  jupiter: '#1f9e3b',
  saturn: '#8a8f9c',
  uranus: '#00a8a8',
  neptune: '#2e86de',
  pluto: '#6c3483',
};

const ANGLE_DASH: Record<string, string | undefined> = {
  MC: undefined,
  IC: '6 6',
  Asc: '1 5',
  Desc: '5 3 1 3',
};

const STAR_ICON = L.divIcon({
  className: '',
  html: '<div style="font-size:26px;line-height:26px;filter:drop-shadow(0 0 4px rgba(0,0,0,.6))">⭐</div>',
  iconSize: [26, 26],
  iconAnchor: [13, 13],
});

function ClickHandler({ onMapClick }: { onMapClick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      const lon = ((e.latlng.lng + 540) % 360) - 180;
      onMapClick(e.latlng.lat, lon);
    },
  });
  return null;
}

type Props = {
  lines: AcgLineFeature[];
  linesVisible: boolean;
  birthMarker: { lat: number; lon: number; label: string };
  clickedPoint?: { lat: number; lon: number };
  onMapClick: (lat: number, lon: number) => void;
};

export default function AstrocartographyMap({
  lines,
  linesVisible,
  birthMarker,
  clickedPoint,
  onMapClick,
}: Props) {
  const segments = useMemo(
    () =>
      lines.map((feature, index) => ({
        key: `${feature.properties.planet}-${feature.properties.angle}-${index}`,
        color: PLANET_COLOR[feature.properties.planet.toLowerCase()] || '#8a7dff',
        dashArray: ANGLE_DASH[feature.properties.angle],
        weight: feature.properties.angle === 'MC' || feature.properties.angle === 'IC' ? 2 : 1.6,
        positions: feature.geometry.coordinates.map(([lon, lat]) => [lat, lon] as [number, number]),
      })),
    [lines]
  );

  return (
    <MapContainer
      center={[birthMarker.lat, birthMarker.lon]}
      zoom={4}
      minZoom={2}
      worldCopyJump
      className="h-full w-full"
    >
      <TileLayer
        attribution="&copy; OpenStreetMap, &copy; CARTO"
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        subdomains="abcd"
        maxZoom={10}
      />
      {linesVisible &&
        segments.map((segment) => (
          <Polyline
            key={segment.key}
            positions={segment.positions}
            pathOptions={{
              color: segment.color,
              weight: segment.weight,
              opacity: segment.dashArray ? 0.55 : 0.7,
              dashArray: segment.dashArray,
            }}
          />
        ))}
      <Marker position={[birthMarker.lat, birthMarker.lon]} icon={STAR_ICON}>
      </Marker>
      {clickedPoint && (
        <CircleMarker
          center={[clickedPoint.lat, clickedPoint.lon]}
          radius={7}
          pathOptions={{ color: '#fff', weight: 2, fillColor: '#8a7dff', fillOpacity: 1 }}
        />
      )}
      <ClickHandler onMapClick={onMapClick} />
    </MapContainer>
  );
}
