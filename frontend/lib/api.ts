export type ShortenResult = { short_code: string; short_url: string };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function shortenUrl(url: string, apiUrl: string = API_URL): Promise<ShortenResult> {
  const base = apiUrl.replace(/\/+$/, "");
  let res: Response;
  try {
    res = await fetch(`${base}/shorten`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
  } catch {
    throw new Error("Could not reach the server. Please try again.");
  }
  if (res.status === 422) throw new Error("Please enter a valid http(s) URL.");
  if (!res.ok) throw new Error(`Server error (${res.status}). Please try again.`);

  let data: unknown;
  try {
    data = await res.json();
  } catch {
    throw new Error("Unexpected response from server. Please try again.");
  }
  if (
    typeof (data as ShortenResult)?.short_url !== "string" ||
    typeof (data as ShortenResult)?.short_code !== "string"
  ) {
    throw new Error("Unexpected response from server. Please try again.");
  }
  return data as ShortenResult;
}
