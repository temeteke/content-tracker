export interface ContentItem {
  id: string
  title: string
  content_type: string
  parent_id: string | null
  status: string
  description: string
  published_at: string | null
  duration_seconds: number | null
  created_at: string
  updated_at: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api"

export async function listItems(params: {
  status?: string
  contentType?: string
  query?: string
} = {}): Promise<ContentItem[]> {
  const search = new URLSearchParams()
  if (params.status) search.set("status", params.status)
  if (params.contentType) search.set("content_type", params.contentType)
  if (params.query) search.set("query", params.query)

  const suffix = search.size ? `?${search.toString()}` : ""
  const response = await fetch(`${apiBaseUrl}/items${suffix}`)
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`)
  }
  return response.json()
}

export async function updateItemStatus(id: string, status: string): Promise<ContentItem> {
  const response = await fetch(`${apiBaseUrl}/items/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  })
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`)
  }
  return response.json()
}
