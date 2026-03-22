const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function queryAPI(query) {
  let res;
  try {
    res = await fetch(`${BASE_URL}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
  } catch {
    throw new Error(`Cannot reach backend at ${BASE_URL}. Check that the API server is running and CORS is configured.`);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  return res.json();
}

export async function clearCache() {
  const res = await fetch(`${BASE_URL}/cache`, { method: "DELETE" });
  return res.json();
}
