const BASE = process.env.NEXT_PUBLIC_API_BASE || "/api-proxy";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  // Health
  health: () => fetchJSON<{ status: string }>("/api/health"),

  // Brands
  listBrands: () => fetchJSON<any[]>("/api/brands"),
  getBrand: (slug: string) => fetchJSON<any>(`/api/brands/${slug}`),
  analyzeBrand: (url: string, name: string, interactive = false) =>
    fetchJSON<{ run_id: string; sse_url: string }>("/api/brands/analyze", {
      method: "POST",
      body: JSON.stringify({ url, name, interactive }),
    }),
  updateBrand: (slug: string, data: any) =>
    fetchJSON<any>(`/api/brands/${slug}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteBrand: (slug: string) =>
    fetchJSON<any>(`/api/brands/${slug}`, { method: "DELETE" }),

  // Pipelines
  runPipeline: (data: any) =>
    fetchJSON<{ run_id: string; sse_url: string }>("/api/pipelines/run", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listRuns: () => fetchJSON<any[]>("/api/pipelines"),
  getRun: (runId: string) => fetchJSON<any>(`/api/pipelines/${runId}`),
  submitFeedback: (runId: string, approved: boolean, instructions = "") =>
    fetchJSON<any>(`/api/pipelines/${runId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ approved, instructions }),
    }),

  // Outputs
  listOutputs: (params?: { asset_type?: string; run_id?: string }) => {
    const q = new URLSearchParams();
    if (params?.asset_type) q.set("asset_type", params.asset_type);
    if (params?.run_id) q.set("run_id", params.run_id);
    return fetchJSON<any[]>(`/api/outputs?${q}`);
  },
  getRunOutputs: (runId: string) => fetchJSON<any[]>(`/api/outputs/runs/${runId}`),
  getFileUrl: (assetId: number) => `${BASE}/api/outputs/${assetId}/file`,

  // Scripts
  generateScript: (data: any) =>
    fetchJSON<{ run_id: string; sse_url: string }>("/api/scripts/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getScript: (runId: string) => fetchJSON<any>(`/api/scripts/${runId}`),
};
