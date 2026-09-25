import { act, renderHook, waitFor } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { getNotifications } from "../../api/client"
import { setNotificationSession, useNotifications } from "../notificationStore"
vi.mock("../../api/client", () => ({ getNotifications: vi.fn() }))
afterEach(() => { setNotificationSession(false); vi.clearAllMocks() })

it("V39 polls an enabled auth-disabled session without stored credentials and clears on logout", async () => {
  vi.mocked(getNotifications).mockResolvedValue([{ id: "notice", read: false } as Awaited<ReturnType<typeof getNotifications>>[number]])
  const { result, unmount } = renderHook(() => useNotifications())
  expect(getNotifications).not.toHaveBeenCalled()
  act(() => setNotificationSession(true))
  await waitFor(() => expect(result.current).toHaveLength(1))
  expect(localStorage.getItem("aaa_password")).toBeNull()
  act(() => setNotificationSession(false))
  expect(result.current).toEqual([])
  unmount()
})

it("V39 ignores a pending response after logout", async () => {
  let complete!: (value: Awaited<ReturnType<typeof getNotifications>>) => void
  vi.mocked(getNotifications).mockImplementation(() => new Promise(resolve => { complete = resolve }))
  const { result, unmount } = renderHook(() => useNotifications())
  act(() => setNotificationSession(true))
  act(() => setNotificationSession(false))
  await act(async () => complete([{ id: "stale" } as Awaited<ReturnType<typeof getNotifications>>[number]]))
  expect(result.current).toEqual([])
  unmount()
})
