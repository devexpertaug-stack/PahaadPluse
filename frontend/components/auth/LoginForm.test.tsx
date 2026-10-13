import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { LoginForm } from "./LoginForm";

// next/navigation router mock.
const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

// api.login mock.
const login = vi.fn();
vi.mock("@/lib/api", () => ({
  api: { login: (u: string, p: string) => login(u, p) },
}));

// Spy on the session store.
const setSession = vi.fn();
vi.mock("@/lib/auth", () => ({
  setSession: (t: string, u: unknown) => setSession(t, u),
}));

describe("LoginForm", () => {
  beforeEach(() => {
    push.mockReset();
    login.mockReset();
    setSession.mockReset();
  });

  it("renders the branded form with username, password and Sign in", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText(/email or username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByText(/demo credentials/i)).toBeInTheDocument();
  });

  it("calls api.login, stores the session and redirects on success", async () => {
    const user = {
      id: "user-forestseason-owner",
      username: "owner@forestseason.demo",
      display_name: "Forest Season Owner",
      role: "owner",
      property_id: "mus-forestseason",
      property_name: "The Forest Season Resort",
    };
    login.mockResolvedValueOnce({ token: "tok-123", user });

    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email or username/i), {
      target: { value: "owner@forestseason.demo" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "ForestSeason@2024" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith(
        "owner@forestseason.demo",
        "ForestSeason@2024",
      );
      expect(setSession).toHaveBeenCalledWith("tok-123", user);
      expect(push).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("shows an inline error on failed login", async () => {
    login.mockRejectedValueOnce(new Error("401"));
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email or username/i), {
      target: { value: "owner@forestseason.demo" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/invalid username or password/i);
    });
    expect(push).not.toHaveBeenCalled();
  });
});
