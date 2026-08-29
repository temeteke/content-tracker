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

export interface ConsumptionHistory {
  id: string
  content_item_id: string
  consumed_at: string
  rating: number | null
  comment: string
  created_at: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api"

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `API request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

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
  return parseResponse<ContentItem[]>(await fetch(`${apiBaseUrl}/items${suffix}`))
}

export async function createItem(payload: {
  title: string
  content_type: string
  status?: string
}): Promise<ContentItem> {
  return parseResponse<ContentItem>(
    await fetch(`${apiBaseUrl}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  )
}

export async function updateItemStatus(id: string, status: string): Promise<ContentItem> {
  return parseResponse<ContentItem>(
    await fetch(`${apiBaseUrl}/items/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }),
  )
}

export async function addConsumptionHistory(
  id: string,
  payload: {
    consumed_at: string
    rating: number | null
    comment: string
  },
): Promise<ConsumptionHistory> {
  return parseResponse<ConsumptionHistory>(
    await fetch(`${apiBaseUrl}/items/${id}/history`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  )
}
