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

export async function listItems(): Promise<ContentItem[]> {
  const response = await fetch(`${apiBaseUrl}/items`)
  if (!response.ok) throw new Error(`API request failed: ${response.status}`)
  return response.json()
}
