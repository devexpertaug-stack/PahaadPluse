"use client";

import "leaflet/dist/leaflet.css";
import { useEffect, useRef, useState } from "react";
import type { Hotspot } from "@/lib/api";

export interface HotspotMapProps {
  hotspots: Hotspot[];
  selected: string | null;
  onSelect: (canonical: string) => void;
}

const MUSSOORIE_CENTER: [number, number] = [30.4599, 78.0644];

/**
 * Leaflet + OpenStreetMap heatmap of destination hotspots.
 *
 * Leaflet is imported dynamically on the client only (it touches `window`), so
 * this component renders nothing meaningful during SSR/tests. If Leaflet or the
 * OSM tiles are unreachable the map degrades gracefully to a styled list of
 * geocoded hotspots so the page still renders.
 */
export function HotspotMap({ hotspots, selected, onSelect }: HotspotMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<ReturnType<typeof import("leaflet").map> | null>(null);
  const layerRef = useRef<ReturnType<typeof import("leaflet").layerGroup> | null>(
    null,
  );
  const [failed, setFailed] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let L: typeof import("leaflet");

    async function init() {
      try {
        L = await import("leaflet");
        if (cancelled || !containerRef.current) return;
        if (!mapRef.current) {
          const map = L.map(containerRef.current, {
            center: MUSSOORIE_CENTER,
            zoom: 13,
            scrollWheelZoom: false,
          });
          L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "© OpenStreetMap contributors",
            maxZoom: 18,
          }).addTo(map);
          mapRef.current = map;
        }
        setReady(true);
      } catch {
        if (!cancelled) setFailed(true);
      }
    }
    void init();
    return () => {
      cancelled = true;
      const map = mapRef.current;
      if (map) {
        map.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Draw / redraw markers whenever hotspots change.
  useEffect(() => {
    if (!ready || failed) return;
    let cancelled = false;
    async function draw() {
      const L = await import("leaflet");
      const map = mapRef.current;
      if (!map || cancelled) return;
      if (layerRef.current) map.removeLayer(layerRef.current);
      const group = L.layerGroup();
      const max = Math.max(1, ...hotspots.map((h) => h.negative_count));
      hotspots.forEach((h) => {
        const radius = 10 + (h.negative_count / max) * 24;
        const isSel = h.canonical === selected;
        const circle = L.circleMarker([h.latitude, h.longitude], {
          radius,
          color: isSel ? "#0f5f44" : "#b3261e",
          weight: isSel ? 3 : 1,
          fillColor: "#b3261e",
          fillOpacity: 0.45,
        });
        circle.bindTooltip(
          `${h.label}: ${h.negative_count} negative mention(s)`,
        );
        circle.on("click", () => onSelect(h.canonical));
        group.addLayer(circle);
      });
      group.addTo(map);
      layerRef.current = group;
    }
    void draw();
    return () => {
      cancelled = true;
    };
  }, [hotspots, selected, ready, failed, onSelect]);

  if (failed) {
    return (
      <div className="rounded-2xl border border-mist-300 bg-mist-50 p-4">
        <p className="mb-3 text-sm text-forest-600">
          Map tiles are unavailable right now. Showing geocoded hotspots as a
          list instead.
        </p>
        <ul className="space-y-2">
          {hotspots.map((h) => (
            <li key={h.canonical}>
              <button
                type="button"
                onClick={() => onSelect(h.canonical)}
                className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm ${
                  h.canonical === selected
                    ? "bg-forest-100 text-forest-800"
                    : "bg-mist-100 text-forest-700 hover:bg-mist-200"
                }`}
              >
                <span className="font-medium">{h.label}</span>
                <span className="text-xs text-forest-500">
                  {h.negative_count} negative · {h.distinct_properties} properties
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      role="application"
      aria-label="Destination hotspot heatmap"
      className="h-[420px] w-full overflow-hidden rounded-2xl border border-mist-300"
      style={{ background: "#e2efed" }}
    />
  );
}
