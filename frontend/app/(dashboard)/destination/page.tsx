"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { PageHeader, Card, Badge, StatTile, Button } from "@/components/ui";
import {
  api,
  DESTINATION_THEMES,
  type HeatmapResponse,
  type HotspotQuote,
} from "@/lib/api";
import snapshot from "@/lib/sentinelSnapshot.json";

const HotspotMap = dynamic(
  () => import("@/components/destination/HotspotMap").then((m) => m.HotspotMap),
  { ssr: false, loading: () => <MapSkeleton /> },
);

const SNAPSHOT = snapshot.heatmap as unknown as HeatmapResponse;

function MapSkeleton() {
  return (
    <div className="flex h-[420px] w-full items-center justify-center rounded-2xl border border-mist-300 bg-mist-100 text-sm text-forest-500">
      Loading hill-town map…
    </div>
  );
}

export default function DestinationPage() {
  const [data, setData] = useState<HeatmapResponse>(SNAPSHOT);
  const [theme, setTheme] = useState<string>("");
  const [start, setStart] = useState<string>("");
  const [end, setEnd] = useState<string>("");
  const [selected, setSelected] = useState<string | null>(null);
  const [quotes, setQuotes] = useState<HotspotQuote[]>([]);
  const [live, setLive] = useState(false);
  const [language, setLanguage] = useState<"en" | "hi">("en");

  const fetchHeatmap = useMemo(
    () => (t: string, s: string, e: string) => {
      api
        .heatmap({
          theme: t || undefined,
          start: s || undefined,
          end: e || undefined,
        })
        .then((res) => {
          setData(res);
          setLive(true);
        })
        .catch(() => {
          /* keep the bundled snapshot offline */
        });
    },
    [],
  );

  useEffect(() => {
    fetchHeatmap(theme, start, end);
  }, [theme, start, end, fetchHeatmap]);

  useEffect(() => {
    if (!selected) {
      setQuotes([]);
      return;
    }
    api
      .hotspotQuotes(selected, {
        theme: theme || undefined,
        start: start || undefined,
        end: end || undefined,
      })
      .then((res) => setQuotes(res.quotes))
      .catch(() => setQuotes([]));
  }, [selected, theme, start, end]);

  const hotspots = data.hotspots ?? [];
  const totalNegative = data.total_negative_mentions ?? 0;

  return (
    <div>
      <PageHeader
        eyebrow="Destination Lens · F8"
        title="Destination Lens"
        description="A geocoded heatmap of negative guest mentions across Mussoorie's landmarks. Filter by issue theme and date range, then generate an Evidence Packet for the authorities."
        actions={
          <Badge tone={live ? "forest" : "dawn"}>
            {live ? "Live from API" : "Sample snapshot"}
          </Badge>
        }
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Hotspots" value={hotspots.length} hint="geocoded landmarks" />
        <StatTile
          label="Negative mentions"
          value={totalNegative}
          trend="down"
          hint={theme ? `theme: ${theme}` : "all themes"}
        />
        <StatTile
          label="Themes tracked"
          value={DESTINATION_THEMES.length}
          hint="traffic · parking · water …"
        />
        <StatTile
          label="Gazetteer"
          value="Mussoorie"
          hint="Uttarakhand hill town"
        />
      </div>

      <Card
        title="Filters"
        subtitle="Narrow the heatmap by issue theme and date range (Req 14.3)"
        className="mb-6"
      >
        <div className="flex flex-wrap items-end gap-4">
          <label className="text-sm">
            <span className="mb-1 block font-medium text-forest-700">Issue theme</span>
            <select
              aria-label="Issue theme filter"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="rounded-lg border border-mist-300 bg-mist-50 px-3 py-2 text-sm text-forest-800"
            >
              <option value="">All themes</option>
              {DESTINATION_THEMES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium text-forest-700">From</span>
            <input
              type="date"
              aria-label="Start date filter"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className="rounded-lg border border-mist-300 bg-mist-50 px-3 py-2 text-sm text-forest-800"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium text-forest-700">To</span>
            <input
              type="date"
              aria-label="End date filter"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className="rounded-lg border border-mist-300 bg-mist-50 px-3 py-2 text-sm text-forest-800"
            />
          </label>
          <Button
            variant="ghost"
            onClick={() => {
              setTheme("");
              setStart("");
              setEnd("");
            }}
          >
            Reset
          </Button>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card
          title="Negative-mention heatmap"
          subtitle="Larger, darker markers mean more negative mentions (react-leaflet + OSM)"
        >
          <HotspotMap
            hotspots={hotspots}
            selected={selected}
            onSelect={setSelected}
          />
          <div className="mt-3 flex flex-wrap gap-2">
            {hotspots.map((h) => (
              <button
                key={h.canonical}
                type="button"
                onClick={() => setSelected(h.canonical)}
                className={`rounded-full border px-3 py-1 text-xs font-medium ${
                  h.canonical === selected
                    ? "border-forest-500 bg-forest-100 text-forest-800"
                    : "border-mist-300 bg-mist-50 text-forest-600 hover:bg-mist-100"
                }`}
              >
                {h.label} · {h.negative_count}
              </button>
            ))}
          </div>
        </Card>

        <Card
          title={selected ? `Hotspot: ${selected}` : "Select a hotspot"}
          subtitle="Public quotes and the Evidence Packet (pseudonyms + PII excluded)"
        >
          {!selected ? (
            <p className="text-sm text-forest-600">
              Click a marker or chip to inspect a hotspot, review the guest
              quotes behind it and generate an Evidence Packet for the
              authorities.
            </p>
          ) : (
            <div>
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <label className="text-sm">
                  <span className="mb-1 block font-medium text-forest-700">
                    Packet language
                  </span>
                  <select
                    aria-label="Evidence packet language"
                    value={language}
                    onChange={(e) =>
                      setLanguage(e.target.value as "en" | "hi")
                    }
                    className="rounded-lg border border-mist-300 bg-mist-50 px-3 py-2 text-sm text-forest-800"
                  >
                    <option value="en">English</option>
                    <option value="hi">हिंदी (Devanagari)</option>
                  </select>
                </label>
                <a
                  href={api.evidencePacketUrl(selected, {
                    theme: theme || undefined,
                    start: start || undefined,
                    end: end || undefined,
                    language,
                  })}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Button>Generate Evidence Packet (PDF)</Button>
                </a>
              </div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-forest-500">
                Representative quotes
              </p>
              <ul className="space-y-2">
                {quotes.length === 0 ? (
                  <li className="text-sm text-forest-500">
                    No quotes in the current filter window.
                  </li>
                ) : (
                  quotes.map((q, i) => (
                    <li
                      key={i}
                      className="rounded-lg bg-mist-100 px-3 py-2 text-sm"
                    >
                      <p className="text-forest-800">“{q.text}”</p>
                      <p className="mt-1 text-xs text-forest-500">
                        {q.platform} · {q.date}
                        {q.source_url ? (
                          <>
                            {" · "}
                            <a
                              href={q.source_url}
                              className="text-forest-600 underline"
                              target="_blank"
                              rel="noreferrer"
                            >
                              source
                            </a>
                          </>
                        ) : (
                          " · source URL unavailable"
                        )}
                      </p>
                    </li>
                  ))
                )}
              </ul>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
