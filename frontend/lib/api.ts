/**
 * Typed fetch client for the PahadPulse FastAPI backend.
 *
 * The base URL comes from `NEXT_PUBLIC_API_BASE_URL` (set by `make demo`) and
 * defaults to the local API port.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed with ${res.status}`);
  }
  return (await res.json()) as T;
}

export interface PropertyCounts {
  property_id: string;
  property_name: string;
  total: number;
  per_platform: Record<string, number>;
  missing_source_url: number;
}

export interface ReviewCountsResponse {
  properties: PropertyCounts[];
}

export interface ReviewSummary {
  id: string;
  platform: string;
  property_id: string;
  property_name: string;
  author_pseudonym: string;
  date: string;
  native_rating: number;
  normalised_rating: number;
  text: string;
  detected_language: string;
  script: string;
  overall_sentiment: string | null;
  source_url: string | null;
  source_url_available: boolean;
}

export interface UnmappedCategory {
  platform: string;
  category: string;
  count: number;
}

export const PLATFORMS = [
  "Google",
  "MakeMyTrip",
  "Booking.com",
  "TripAdvisor",
  "Agoda",
] as const;

// ---- Analytics (Deep features) types ----
export interface TrendBucket {
  period: string;
  positive: number;
  neutral: number;
  negative: number;
  total: number;
  complaint_percentage: number | null;
  no_data: boolean;
}

export interface AspectTrend {
  aspect: string;
  buckets: TrendBucket[];
}

export interface TrendsResponse {
  granularity: string;
  start: string;
  end: string;
  platforms: string[];
  trends: AspectTrend[];
}

export interface Estimate {
  point: number;
  lower: number;
  upper: number;
}

export interface DecompositionCell {
  property_id: string;
  aspect: string;
  month: string;
  mentions: number;
  modelled_score: number;
  market_wide: Estimate;
  property_specific: Estimate;
  rhat: number;
  unreliable: boolean;
  insufficient_data: boolean;
}

export interface DecompositionResponse {
  fitted_at: string;
  cluster_size: number;
  insufficient_cluster: boolean;
  failure: boolean;
  failure_reason: string | null;
  stale_timestamp: string | null;
  cells: DecompositionCell[];
}

export interface Changepoint {
  property_id: string;
  aspect: string | null;
  series: string;
  date: string;
  direction: string;
  posterior: number;
  unreliable: boolean;
  time_to_identification_days: number | null;
}

export interface ChangepointNotification {
  property_id: string;
  aspect: string | null;
  series: string;
  date: string;
  message: string;
  time_machine_link: string;
}

export interface ChangepointsResponse {
  ran_at: string;
  failure: boolean;
  last_successful_run: string | null;
  changepoints: Changepoint[];
  notifications: ChangepointNotification[];
  skipped: {
    property_id: string;
    aspect: string | null;
    series: string;
    label: string;
    points: number;
  }[];
}

export interface DriverWeight {
  aspect: string;
  weight: number;
  lower: number;
  upper: number;
  available: boolean;
  abs_weight: number;
}

export interface WhatIfModel {
  platform: string;
  current_rating: number;
  review_count: number;
  low_confidence: boolean;
  estimated_at: string;
  home_property_id: string;
  driver_weights: DriverWeight[];
  cluster_size: number;
}

export interface WhatIfProjection {
  platform: string;
  current_rating: number;
  projected_rating: number;
  projected_lower: number;
  projected_upper: number;
  projected_rank: number;
  cluster_size: number;
  low_confidence: boolean;
  applied_deltas: { aspect: string; delta: number }[];
}

export interface TimeMachineQuote {
  span: string;
  platform: string;
  date: string;
  source_url: string | null;
  window: string;
}

export interface TimeMachineResponse {
  changepoint: Changepoint | null;
  message: string | null;
  causes: {
    phrase: string;
    lift: number;
    before_count: number;
    after_count: number;
  }[];
  before_quotes: TimeMachineQuote[];
  after_quotes: TimeMachineQuote[];
  limited_evidence: boolean;
  scope_label: string;
  interventions: { date: string; label: string; property_id: string }[];
  failed: boolean;
}

export interface PlaybookTheme {
  aspect: string;
  leader_positive_count: number;
  home_positive_count: number;
  home_negative_count: number;
  quotes: { span: string; platform: string; date: string; source_url: string }[];
}

export interface PlaybookLagging {
  aspect: string;
  home_upper: number;
  leader_lower: number;
  themes: PlaybookTheme[];
  action_paragraph: string;
  action_template_generated: boolean;
}

export interface PlaybookResponse {
  home_property_id: string;
  home_property_name: string;
  leader_property_id: string;
  leader_property_name: string;
  message: string | null;
  lagging: PlaybookLagging[];
  undetermined: { aspect: string; reason: string }[];
}

export interface GapTheme {
  aspect: string;
  affected_properties: number;
  cluster_size: number;
  total_negatives: number;
  destination_median: number;
  trend: { month: string; negative_share: number | null }[];
  quotes: {
    span: string;
    platform: string;
    date: string;
    property_id: string;
    source_url: string | null;
  }[];
  market_gap: boolean;
}

export interface GapFinderResponse {
  cluster_size: number;
  themes: GapTheme[];
}

export interface BenchmarkMetric {
  macro_f1: number;
  ci_95: [number, number];
}

export interface BenchmarkSystem {
  name: string;
  overall_sentiment: BenchmarkMetric;
  aspect_detection: BenchmarkMetric;
  aspect_sentiment: BenchmarkMetric;
  confusion_matrix: Record<string, Record<string, number>>;
  aspect_confusion: Record<
    string,
    { matrix: Record<string, Record<string, number>>; support: { n: number } }
  >;
}

export interface BenchmarkResponse {
  seed: number;
  test_set_size: number;
  systems: BenchmarkSystem[];
}

export const ASPECTS = [
  "Food",
  "Room",
  "Housekeeping",
  "Staff",
  "Location",
  "Service",
  "Value_for_Money",
  "Cleanliness",
  "Booking_Experience",
] as const;

// ---- Destination Lens (F8) types ----
export interface Hotspot {
  canonical: string;
  label: string;
  latitude: number;
  longitude: number;
  negative_count: number;
  total_count: number;
  themes: Record<string, number>;
  distinct_properties: number;
}

export interface HeatmapResponse {
  destination: string;
  theme: string | null;
  themes_available: string[];
  start: string | null;
  end: string | null;
  hotspots: Hotspot[];
  total_negative_mentions: number;
}

export interface HotspotQuote {
  text: string;
  platform: string;
  date: string;
  source_url: string | null;
  property_name: string;
}

export const DESTINATION_THEMES = [
  "traffic",
  "parking",
  "water",
  "garbage",
  "road condition",
  "safety",
] as const;

// ---- In-Stay Sentinel types ----
export interface RiskFactor {
  label: string;
  contribution: number;
}

export interface BoardRow {
  stay_id: string;
  room: string;
  guest_pseudonym: string;
  hours_to_checkout: number;
  score: number;
  high_risk: boolean;
  pinned: boolean;
  top_factors: RiskFactor[];
  top_open_complaint: {
    id: string;
    issue_type: string;
    urgency: string;
    department: string;
    text: string;
  } | null;
  responsible_department: string | null;
  sop_action: string | null;
}

export interface BoardResponse {
  generated_at: string;
  high_risk_threshold: number;
  rows: BoardRow[];
}

export interface SentinelMetrics {
  avg_complaint_to_department_seconds: number;
  in_stay_resolution_rate: number;
  repeat_complaints_this_week: number;
  total_complaints: number;
  resolved_complaints: number;
  open_complaints: number;
}

export interface SOPView {
  department: string;
  issue_type: string;
  corrective_steps: string[];
  target_resolution_minutes: number;
}

export interface ComplaintView {
  id: string;
  stay_id: string | null;
  room: string | null;
  guest_pseudonym: string | null;
  channel: string;
  text: string;
  language: string;
  transcript: string | null;
  transcript_translation_en: string | null;
  transcription_confidence: number | null;
  flagged_for_staff: boolean;
  created_at: string;
  assigned_at: string | null;
  resolved_at: string | null;
  department: string | null;
  original_predicted_department: string | null;
  department_confidence: number | null;
  urgency: string | null;
  issue_type: string | null;
  requires_manual_assignment: boolean;
  state: string;
  is_recurrence: boolean;
  recurrence_of: string | null;
  escalated: boolean;
  resolution_note: string | null;
  reassignments: { from: string; to: string; reason: string; at: string }[];
  sop: SOPView | null;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  // Destination Lens
  heatmap: (params?: { theme?: string; start?: string; end?: string }) => {
    const q = new URLSearchParams();
    if (params?.theme) q.set("theme", params.theme);
    if (params?.start) q.set("start", params.start);
    if (params?.end) q.set("end", params.end);
    const qs = q.toString();
    return request<HeatmapResponse>(`/destination/heatmap${qs ? `?${qs}` : ""}`);
  },
  hotspotQuotes: (
    canonical: string,
    params?: { theme?: string; start?: string; end?: string },
  ) => {
    const q = new URLSearchParams();
    if (params?.theme) q.set("theme", params.theme);
    if (params?.start) q.set("start", params.start);
    if (params?.end) q.set("end", params.end);
    const qs = q.toString();
    return request<{ canonical: string; quotes: HotspotQuote[] }>(
      `/destination/hotspots/${encodeURIComponent(canonical)}/quotes${qs ? `?${qs}` : ""}`,
    );
  },
  evidencePacketUrl: (
    canonical: string,
    params?: { theme?: string; start?: string; end?: string; language?: string },
  ) => {
    const q = new URLSearchParams({ canonical, role: "destination_official" });
    if (params?.theme) q.set("theme", params.theme);
    if (params?.start) q.set("start", params.start);
    if (params?.end) q.set("end", params.end);
    if (params?.language) q.set("language", params.language);
    return `${API_BASE_URL}/destination/evidence-packet?${q.toString()}`;
  },
  // Sentinel
  board: () => request<BoardResponse>("/sentinel/board"),
  sentinelMetrics: () => request<SentinelMetrics>("/sentinel/metrics"),
  complaints: () =>
    request<{ complaints: ComplaintView[] }>("/sentinel/complaints"),
  resolveComplaint: (id: string, note: string) =>
    request<{ complaint: ComplaintView }>(
      `/sentinel/complaints/${encodeURIComponent(id)}/resolve`,
      { method: "POST", body: JSON.stringify({ note }) },
    ),
  demoWhatsapp: (body: { from_number: string; body: string; language: string }) =>
    request<{ complaint: ComplaintView; acknowledgement: string | null; risk: number | null }>(
      "/sentinel/demo/whatsapp",
      { method: "POST", body: JSON.stringify(body) },
    ),
  reviewCounts: () =>
    request<ReviewCountsResponse>("/market-radar/review-counts"),
  propertyReviews: (propertyId: string, platform?: string) =>
    request<{ property_id: string; reviews: ReviewSummary[] }>(
      `/market-radar/properties/${encodeURIComponent(propertyId)}/reviews` +
        (platform ? `?platform=${encodeURIComponent(platform)}` : ""),
    ),
  unmappedCategories: (threshold = 20) =>
    request<{ threshold: number; categories: UnmappedCategory[] }>(
      `/market-radar/admin/unmapped-categories?threshold=${threshold}`,
    ),
  trends: (params?: {
    granularity?: string;
    platforms?: string[];
    start?: string;
    end?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.granularity) q.set("granularity", params.granularity);
    if (params?.start) q.set("start", params.start);
    if (params?.end) q.set("end", params.end);
    (params?.platforms ?? []).forEach((p) => q.append("platform", p));
    const qs = q.toString();
    return request<TrendsResponse>(
      `/market-radar/analytics/trends${qs ? `?${qs}` : ""}`,
    );
  },
  decomposition: () =>
    request<DecompositionResponse>("/market-radar/analytics/decomposition"),
  changepoints: () =>
    request<ChangepointsResponse>("/market-radar/analytics/changepoints"),
  whatIfModel: (platform: string) =>
    request<WhatIfModel>(
      `/market-radar/analytics/what-if/${encodeURIComponent(platform)}`,
    ),
  whatIfProject: (platform: string, deltas: Record<string, number>) =>
    request<WhatIfProjection>(
      `/market-radar/analytics/what-if/${encodeURIComponent(platform)}/project`,
      { method: "POST", body: JSON.stringify({ deltas }) },
    ),
  timeMachine: (propertyId: string, at: string, aspect?: string) => {
    const q = new URLSearchParams({ property_id: propertyId, at });
    if (aspect) q.set("aspect", aspect);
    return request<TimeMachineResponse>(
      `/market-radar/analytics/time-machine?${q.toString()}`,
    );
  },
  playbook: () =>
    request<PlaybookResponse>("/market-radar/analytics/playbook"),
  gapFinder: () =>
    request<GapFinderResponse>("/market-radar/analytics/gap-finder"),
  benchmark: () =>
    request<BenchmarkResponse>("/market-radar/analytics/benchmark"),
};
