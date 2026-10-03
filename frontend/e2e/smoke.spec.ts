import { expect, test } from "@playwright/test"

const apiBase = process.env.E2E_API_URL ?? "http://localhost:8000/api"

async function api(path: string, init?: RequestInit) {
  const response = await fetch(`${apiBase}${path}`, init)
  if (!response.ok) {
    throw new Error(`API ${path} failed: ${response.status}`)
  }
  if (response.status === 204) return null
  return response.json()
}

test("smoke: list, create, status change, history", async ({ page }) => {
  const timestamp = Date.now()
  const title = `E2E Smoke ${timestamp}`

  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Content" })).toBeVisible()

  const created = (await api("/items", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, content_type: "video" }),
  })) as { id: string; revision: number }

  const search = page.getByRole("textbox", { name: "Search" })
  await search.fill(title)
  await search.press("Enter")
  await expect(page.getByText(title).first()).toBeVisible()

  await page.getByText(title).first().click()
  await expect(page.getByRole("heading", { name: title })).toBeVisible()

  await api(`/items/${created.id}/history`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      consumed_at: new Date().toISOString(),
      rating: 5,
      comment: "e2e smoke",
    }),
  })

  await page.reload()
  await expect(page.getByText("e2e smoke").first()).toBeVisible()

  const latest = (await api(`/items/${created.id}`)) as { revision: number }
  await api(`/items/${created.id}?revision=${latest.revision}`, {
    method: "DELETE",
  })
  await page.goto("/")
  await expect(page.getByText(title)).toHaveCount(0)
})
