export interface ContentItem {
  id: string
  title: string
  content_type: string
  parent_id: string | null
  status: string
  description: string
  published_at: string | null
  duration_seconds: number | null
  revision: number
  created_at: string
  updated_at: string
}

export interface ContentLink {
  id: string
  content_item_id: string
  url: string
  link_type: string
  created_at: string
}

export interface ConsumptionHistory {
  id: string
  content_item_id: string
  consumed_at: string
  rating: number | null
  comment: string
  created_at: string
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

export function formatApiError(cause: unknown, fallback: string): string {
  if (cause instanceof ApiError) {
    if (cause.status === 409) return `${cause.message} Reloading the latest data.`
    return cause.message
  }
  return cause instanceof Error ? cause.message : fallback
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api"

function extractMessage(status: number, body: unknown): string {
  if (body !== null && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === "string" && detail) return detail
    if (Array.isArray(detail) && detail.length > 0) {
      const parts = detail.map((entry) => {
        if (entry !== null && typeof entry === "object" && "msg" in entry) {
          const record = entry as { loc?: unknown; msg: unknown }
          const location = Array.isArray(record.loc) ? record.loc.join(".") : ""
          const prefix = location ? `${location}: ` : ""
          return `${prefix}${String(record.msg)}`
        }
        return JSON.stringify(entry)
      })
      return parts.join("; ")
    }
  }
  return `API request failed: ${status}`
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T
  const text = await response.text()
  let body: unknown = null
  try {
    body = text ? (JSON.parse(text) as unknown) : null
  } catch {
    body = null
  }
  if (!response.ok) {
    throw new ApiError(response.status, extractMessage(response.status, body ?? text))
  }
  return (body ?? undefined) as T
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return parseResponse<T>(await fetch(`${apiBaseUrl}${path}`, init))
}

function jsonBody(payload: unknown): RequestInit {
  return {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }
}

export const ITEMS_PAGE_SIZE = 100

export interface ListItemsParams {
  status?: string
  contentType?: string
  query?: string
  parentId?: string
  offset?: number
  limit?: number
}

export interface ListItemsResult {
  items: ContentItem[]
  total: number | null
}

export async function listItems(params: ListItemsParams = {}): Promise<ListItemsResult> {
  const search = new URLSearchParams()
  if (params.status) search.set("status", params.status)
  if (params.contentType) search.set("content_type", params.contentType)
  if (params.query) search.set("query", params.query)
  if (params.parentId) search.set("parent_id", params.parentId)
  search.set("limit", String(params.limit ?? ITEMS_PAGE_SIZE))
  search.set("offset", String(params.offset ?? 0))

  const response = await fetch(`${apiBaseUrl}/items?${search.toString()}`)
  if (!response.ok) {
    const text = await response.text()
    let body: unknown = null
    try {
      body = text ? (JSON.parse(text) as unknown) : null
    } catch {
      body = null
    }
    throw new ApiError(response.status, extractMessage(response.status, body ?? text))
  }
  const totalHeader = response.headers.get("X-Total-Count")
  const total = totalHeader !== null && totalHeader !== "" ? Number(totalHeader) : null
  let items: ContentItem[]
  try {
    items = (await response.json()) as ContentItem[]
  } catch {
    throw new ApiError(response.status, `API request failed: ${response.status}`)
  }
  return {
    items,
    total: total !== null && Number.isFinite(total) ? total : null,
  }
}

export async function getItem(id: string): Promise<ContentItem> {
  return request<ContentItem>(`/items/${id}`)
}

export async function createItem(payload: {
  title: string
  content_type: string
  status?: string
  parent_id?: string | null
  description?: string
}): Promise<ContentItem> {
  return request<ContentItem>(`/items`, { method: "POST", ...jsonBody(payload) })
}

export async function patchItem(
  id: string,
  payload: {
    revision: number
    title?: string
    content_type?: string
    status?: string
    description?: string
    parent_id?: string | null
  },
): Promise<ContentItem> {
  return request<ContentItem>(`/items/${id}`, { method: "PATCH", ...jsonBody(payload) })
}

export async function deleteItem(id: string, revision: number): Promise<void> {
  const search = new URLSearchParams({ revision: String(revision) })
  await request<void>(`/items/${id}?${search.toString()}`, { method: "DELETE" })
}

export async function listLinks(itemId: string): Promise<ContentLink[]> {
  return request<ContentLink[]>(`/items/${itemId}/links`)
}

export async function addLink(
  itemId: string,
  payload: { url: string; link_type?: string },
): Promise<ContentLink> {
  return request<ContentLink>(`/items/${itemId}/links`, {
    method: "POST",
    ...jsonBody(payload),
  })
}

export async function deleteLink(linkId: string): Promise<void> {
  await request<void>(`/links/${linkId}`, { method: "DELETE" })
}

export async function listHistory(itemId: string): Promise<ConsumptionHistory[]> {
  return request<ConsumptionHistory[]>(`/items/${itemId}/history`)
}

export async function addConsumptionHistory(
  id: string,
  payload: {
    consumed_at: string
    rating: number | null
    comment: string
  },
): Promise<ConsumptionHistory> {
  return request<ConsumptionHistory>(`/items/${id}/history`, {
    method: "POST",
    ...jsonBody(payload),
  })
}

export async function updateConsumptionHistory(
  historyId: string,
  payload: {
    consumed_at?: string
    rating?: number | null
    comment?: string
  },
): Promise<ConsumptionHistory> {
  return request<ConsumptionHistory>(`/history/${historyId}`, {
    method: "PATCH",
    ...jsonBody(payload),
  })
}

export async function deleteConsumptionHistory(historyId: string): Promise<void> {
  await request<void>(`/history/${historyId}`, { method: "DELETE" })
}

export async function mergeItems(targetId: string, sourceItemId: string): Promise<ContentItem> {
  return request<ContentItem>(`/items/${targetId}/merge`, {
    method: "POST",
    ...jsonBody({ source_item_id: sourceItemId }),
  })
}
