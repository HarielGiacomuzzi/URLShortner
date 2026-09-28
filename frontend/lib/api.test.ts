import { afterEach, describe, expect, it, vi } from "vitest";
import { shortenUrl } from "./api";

const API = "http://api.test";

function mockFetch(impl: () => Promise<Response>) {
  const fn = vi.fn(impl);
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("shortenUrl", () => {
  it("POSTs the url and returns the parsed result", async () => {
    const result = { short_code: "abc123", short_url: "http://api.test/abc123" };
    const fetchFn = mockFetch(async () => new Response(JSON.stringify(result), { status: 200 }));

    await expect(shortenUrl("https://example.com", API)).resolves.toEqual(result);
    expect(fetchFn).toHaveBeenCalledWith(`${API}/shorten`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: "https://example.com" }),
    });
  });

  it("maps 422 to an invalid-URL message", async () => {
    mockFetch(async () => new Response("{}", { status: 422 }));
    await expect(shortenUrl("bad", API)).rejects.toThrow("Please enter a valid http(s) URL.");
  });

  it("maps other non-OK statuses to a server error message", async () => {
    mockFetch(async () => new Response("oops", { status: 500 }));
    await expect(shortenUrl("https://example.com", API)).rejects.toThrow("Server error (500). Please try again.");
  });

  it("maps network failures to a friendly message", async () => {
    mockFetch(async () => {
      throw new TypeError("Failed to fetch");
    });
    await expect(shortenUrl("https://example.com", API)).rejects.toThrow(
      "Could not reach the server. Please try again.",
    );
  });
});
