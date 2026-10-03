import { describe, expect, it, vi } from "vitest"

import { ApiError, formatApiError, ITEMS_PAGE_SIZE, listItems } from "./api"

describe("formatApiError", () => {
  it("returns the message for a generic ApiError", () => {
    expect(formatApiError(new ApiError(422, "title: required"), "fallback")).toBe("title: required")
  })

  it("appends a reload hint for conflicts", () => {
    expect(formatApiError(new ApiError(409, "stale"), "fallback")).toContain("Reloading")
  })

  it("falls back for unknown errors", () => {
    expect(formatApiError("boom", "fallback")).toBe("fallback")
  })
})

describe("listItems", () => {
  it("returns items with the X-Total-Count header", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ id: "1" }]), {
        status: 200,
        headers: { "X-Total-Count": "42", "Content-Type": "application/json" },
      }),
    )
    vi.stubGlobal("fetch", fetchMock)

    const result = await listItems({ limit: 10, offset: 0 })
    expect(result.total).toBe(42)
    expect(result.items).toHaveLength(1)

    const url = String(fetchMock.mock.calls[0]?.[0])
    expect(url).toContain("limit=10")
    expect(url).toContain("offset=0")

    vi.unstubAllGlobals()
  })

  it("treats a missing total header as null", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("[]", {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    )

    const result = await listItems()
    expect(result.total).toBeNull()
    expect(result.items).toEqual([])

    vi.unstubAllGlobals()
  })

  it("uses the default page size", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("[]", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )
    vi.stubGlobal("fetch", fetchMock)

    await listItems()
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(`limit=${ITEMS_PAGE_SIZE}`)

    vi.unstubAllGlobals()
  })

  it("throws ApiError with the server detail message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "link already exists" }), {
          status: 409,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    )

    await expect(listItems()).rejects.toMatchObject({
      name: "ApiError",
      status: 409,
    })

    vi.unstubAllGlobals()
  })
})
