import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import App from "./App";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Birthday Savepoint first slice", () => {
  it("shows sign-in when no session exists", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Not authenticated" }), { status: 401 })));
    render(<App />);
    expect(await screen.findByRole("heading", { name: /pick up where/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/your login id/i)).toBeInTheDocument();
  });

  it("renders a generic sealed placeholder without an ID", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/auth/csrf") return new Response(JSON.stringify({ csrf_token: "csrf" }), { status: 200 });
      if (path === "/api/auth/me") return new Response(JSON.stringify({ display_name: "Test Friend", theme: {} }), { status: 200 });
      if (path === "/api/capsules") return new Response(JSON.stringify([{ year: 2099, state: "sealed", unlock_at: "2099-05-20T00:00:00+00:00" }]), { status: 200 });
      return new Response("{}", { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    expect(await screen.findByRole("heading", { name: /test friend/i })).toBeInTheDocument();
    expect(screen.getByText(/still sealed/i)).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/capsules/"))).toBe(false);
  });
});