import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useProcessingStatus } from "@/hooks/useProcessingStatus";
import { authToken } from "@/lib/auth";
import { TestJwtFactory } from "@/test/test-utils";

type Listener = (event: MessageEvent<string>) => void;

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  listeners = new Map<string, Listener>();
  onerror: (() => void) | null = null;
  close = vi.fn();

  constructor(readonly url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(eventName: string, listener: Listener) {
    this.listeners.set(eventName, listener);
  }

  removeEventListener(eventName: string) {
    this.listeners.delete(eventName);
  }

  emit(eventName: string, payload: unknown) {
    this.listeners.get(eventName)?.(new MessageEvent(eventName, { data: JSON.stringify(payload) }));
  }
}

function ddrDetail(status = "processing", dates = [{ id: "d1", ddr_id: "ddr-1", date: "20241031", status: "queued", created_at: 1, updated_at: 1 }]) {
  return { id: "ddr-1", file_path: "/tmp/a.pdf", status, created_at: 1, dates };
}

describe("useProcessingStatus", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
    vi.stubGlobal("fetch", vi.fn());
    authToken.store(TestJwtFactory.tokenWithExpiration(Math.floor(Date.now() / 1000) + 3600));
  });

  it("loads queued rows, opens EventSource only when work remains, applies date events, and closes", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify(ddrDetail()), { status: 200 }));

    const { result, unmount } = renderHook(() => useProcessingStatus("ddr-1"));

    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
    const source = FakeEventSource.instances[0];
    expect(source.url).toContain("/ddrs/ddr-1/status/stream?access_token=");
    expect(result.current.rows[0].status).toBe("processing");

    act(() => {
      source.emit("date_started", { date: "20241101" });
      source.emit("date_complete", { date: "20241031", status: "success", occurrences_count: 0 });
      source.emit("date_failed", { date: "20241101", error: "Tour Sheet Serial not detected", raw_response_id: "r1" });
      source.emit("processing_complete", {
        total_dates: 2,
        failed_dates: 1,
        warning_dates: 0,
        total_occurrences: 0,
      });
    });

    await waitFor(() => expect(result.current.ddrStatus).toBe("complete"));
    expect(result.current.successCount).toBe(1);
    expect(result.current.failedCount).toBe(1);
    expect(result.current.currentProcessedCount).toBe(2);
    expect(source.close).toHaveBeenCalledTimes(1);

    unmount();

    expect(source.close).toHaveBeenCalledTimes(2);
  });

  it("does not open EventSource when no queued work remains", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify(
          ddrDetail("complete", [
            { id: "d1", ddr_id: "ddr-1", date: "20241031", status: "success", created_at: 1, updated_at: 1 },
          ]),
        ),
        { status: 200 },
      ),
    );

    const { result } = renderHook(() => useProcessingStatus("ddr-1"));

    await waitFor(() => expect(result.current.connectionMode).toBe("closed"));
    expect(FakeEventSource.instances).toHaveLength(0);
    expect(result.current.successCount).toBe(1);
  });

  it("falls back to 3 second polling after SSE error before completion", async () => {
    vi.useFakeTimers();
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify(ddrDetail()), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify(
            ddrDetail("complete", [
              { id: "d1", ddr_id: "ddr-1", date: "20241031", status: "success", created_at: 1, updated_at: 1 },
            ]),
          ),
          { status: 200 },
        ),
      );

    const { result } = renderHook(() => useProcessingStatus("ddr-1"));
    await act(async () => {
      await Promise.resolve();
    });
    expect(FakeEventSource.instances).toHaveLength(1);
    const source = FakeEventSource.instances[0];

    act(() => {
      source.onerror?.();
    });

    expect(source.close).toHaveBeenCalledTimes(1);
    expect(result.current.connectionMode).toBe("polling");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(result.current.ddrStatus).toBe("complete");
    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/api/ddrs/ddr-1", expect.any(Object));

    vi.useRealTimers();
  });
});
