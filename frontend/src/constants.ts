export const statusOptions = [
  { title: "Planned", value: "planned" },
  { title: "Active", value: "active" },
  { title: "Completed", value: "completed" },
  { title: "Dropped", value: "dropped" },
]

export const contentTypeOptions = [
  { title: "Video", value: "video" },
  { title: "TV", value: "tv" },
  { title: "Radio", value: "radio" },
  { title: "Podcast", value: "podcast" },
  { title: "Book", value: "book" },
  { title: "Manga", value: "manga" },
  { title: "Article", value: "article" },
  { title: "Other", value: "other" },
]

export function localDateTimeValue(date = new Date()): string {
  const local = new Date(date)
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset())
  return local.toISOString().slice(0, 16)
}

export function toISOString(value: string): string {
  return new Date(value).toISOString()
}

export function formatDateTime(value: string | null): string {
  if (!value) return "-"
  return new Date(value).toLocaleString()
}
