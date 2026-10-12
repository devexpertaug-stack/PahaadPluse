import { describe, it, expect, vi, beforeEach } from "vitest";

// Control the stored token via the auth module mock.
let storedToken: string | null = null;
const clearSession = vi.fn();
vi.mock("@/lib/auth", () => ({
  getToken: () => storedToken,
  clearSession: () => clearSession(),
}));

import { api } from "@/lib/api";

function mockFetchOnce(body: unknown, ok = true, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("api.login", () => {
  beforeEach(() => {
    storedToken = null;
    clearSession.mockClear();
    vi.unstubAllGlobals();
  });

  it("POSTs credentials to /auth/login and returns token + user", async () => {
    const payload = {
      token: "tok-abc",
      user: {
        id: "u1",
        username: "owner@forestseason.demo",
        display_name: "Forest Season Owner",
        role: "owner",
        property_id: "mus-forestseason",
        property_name: "The Forest Season Resort",
      },
    };
    const fetchMock = mockFetchOnce(payload);

    const result = await api.login("owner@forestseason.demo", "ForestSeason@2024");

    expect(result).toEqual(payload);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/auth/login");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      username: "owner@forestseason.demo",
      password: "ForestSeason@2024",
    });
  });

  it("does not attach an Authorization header when no token is stored", async () => {
    const fetchMock = mockFetchOnce({ status: "ok" });
    await api.health();
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Authorization).toBeUndefined();
  });

  it("attaches a Bearer token when a session exists", async () => {
    storedToken = "tok-xyz";
    const fetchMock = mockFetchOnce({
      id: "u1",
      username: "owner@forestseason.demo",
      display_name: "Forest Season Owner",
      role: "owner",
      property_id: "mus-forestseason",
      property_name: "The Forest Season Resort",
    });
    await api.me();
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/auth/me");
    expect(init.headers.Authorization).toBe("Bearer tok-xyz");
  });

  it("clears the session on a 401 so an expired token bounces to /login", async () => {
    storedToken = "tok-expired";
    mockFetchOnce({ detail: "unauthorized" }, false, 401);
    const assign = vi.fn();
    const originalLocation = window.location;
    // jsdom's location is non-configurable, so replace it wholesale for this test.
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { pathname: "/checkout-shield", assign },
    });

    try {
      await expect(api.me()).rejects.toThrow("401");
      expect(clearSession).toHaveBeenCalledTimes(1);
      expect(assign).toHaveBeenCalledWith("/login");
    } finally {
      Object.defineProperty(window, "location", {
        configurable: true,
        value: originalLocation,
      });
    }
  });

  it("does not clear the session on a non-401 error", async () => {
    storedToken = "tok-xyz";
    mockFetchOnce({ detail: "boom" }, false, 500);
    await expect(api.me()).rejects.toThrow("500");
    expect(clearSession).not.toHaveBeenCalled();
  });
});
