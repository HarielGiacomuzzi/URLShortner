"use client";

import { useState, type FormEvent } from "react";
import { shortenUrl, type ShortenResult } from "@/lib/api";

export default function Home() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<ShortenResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setCopied(false);
    try {
      setResult(await shortenUrl(url));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function onCopy() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.short_url);
      setCopied(true);
    } catch {
      setError("Copy failed. Select the link and copy it manually.");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow sm:p-8">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 sm:text-3xl">URL Shortener</h1>

        <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
          <label htmlFor="url" className="sr-only">
            Long URL
          </label>
          <input
            id="url"
            type="url"
            required
            placeholder="https://example.com/a/very/long/link"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Shortening…" : "Shorten"}
          </button>
        </form>

        {error && (
          <p role="alert" className="mt-4 text-sm text-red-600">
            {error}
          </p>
        )}

        <div aria-live="polite">
          {result && (
            <div className="mt-6 flex flex-col gap-3 rounded-lg bg-gray-100 p-4 sm:flex-row sm:items-center">
              <a
                href={result.short_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 break-all font-mono text-blue-700 underline"
              >
                {result.short_url}
              </a>
              <button
                type="button"
                onClick={onCopy}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-50"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
