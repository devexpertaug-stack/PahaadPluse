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

export const api = {
  health: () => request<HealthResponse>("/health"),
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
};
