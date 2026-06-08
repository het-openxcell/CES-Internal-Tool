import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useCorrections } from "@/hooks/useCorrections";
import { apiClient, type OccurrenceRow } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    apiClient: {
      patchOccurrence: vi.fn(),
    },
  };
});

const patchOccurrence = vi.mocked(apiClient.patchOccurrence);

function occurrence(overrides: Partial<OccurrenceRow> = {}): OccurrenceRow {
  return {
    id: "occ-1",
    ddr_id: "ddr-1",
    well_name: "Montney A",
    surface_location: null,
    type: "Back Ream",
    section: "Main",
    mmd: 2100,
    density: 1.35,
    notes: "original note",
    date: "20241031",
    page_number: 1,
    ...overrides,
  };
}

describe("useCorrections", () => {
  beforeEach(() => {
    patchOccurrence.mockReset();
  });

  it("applies optimistic override before request resolves and keeps returned value on success", async () => {
    let resolvePatch: (row: OccurrenceRow) => void = () => undefined;
    patchOccurrence.mockReturnValue(new Promise((resolve) => {
      resolvePatch = resolve;
    }));

    const { result } = renderHook(() => useCorrections());

    let save: Promise<boolean>;
    act(() => {
      save = result.current.saveCorrection("occ-1", "type", "Washout", "corrected type");
    });

    expect(result.current.overrides["occ-1"]).toEqual({ type: "Washout" });
    expect(result.current.correctedIds.has("occ-1")).toBe(true);
    expect(patchOccurrence).toHaveBeenCalledWith("occ-1", "type", "Washout", "corrected type");

    await act(async () => {
      resolvePatch(occurrence({ type: "Washout" }));
      expect(await save!).toBe(true);
    });

    expect(result.current.overrides["occ-1"]?.type).toBe("Washout");
    expect(result.current.errors["occ-1"]).toBeUndefined();
  });

  it("reverts optimistic state and sets row error on failure", async () => {
    patchOccurrence.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useCorrections());

    await act(async () => {
      await expect(result.current.saveCorrection("occ-1", "section", "Surface Hole", "bad section")).rejects.toThrow("boom");
    });

    expect(result.current.overrides["occ-1"]).toBeUndefined();
    expect(result.current.correctedIds.has("occ-1")).toBe(false);
    expect(result.current.errors["occ-1"]).toBe("Couldn't save correction — try again");
  });

  it("parses numeric fields before saving", async () => {
    patchOccurrence.mockResolvedValue(occurrence({ mmd: 2450 }));
    const { result } = renderHook(() => useCorrections());

    await act(async () => {
      await result.current.saveCorrection("occ-1", "mmd", "2450", "corrected mmd");
    });

    expect(result.current.overrides["occ-1"]?.mmd).toBe(2450);
  });

  it("rejects invalid numeric values without calling API", async () => {
    const { result } = renderHook(() => useCorrections());

    await act(async () => {
      await expect(result.current.saveCorrection("occ-1", "density", "bad", "invalid density")).rejects.toThrow("Invalid correction value");
    });

    expect(patchOccurrence).not.toHaveBeenCalled();
    expect(result.current.overrides["occ-1"]).toBeUndefined();
  });

  it("rejects blank values without calling API", async () => {
    const { result } = renderHook(() => useCorrections());

    await act(async () => {
      await expect(result.current.saveCorrection("occ-1", "notes", "   ", "blank notes")).rejects.toThrow("Invalid correction value");
    });

    expect(patchOccurrence).not.toHaveBeenCalled();
  });

  it("clears row errors", async () => {
    patchOccurrence.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useCorrections());

    await act(async () => {
      await expect(result.current.saveCorrection("occ-1", "type", "Washout", "bad type")).rejects.toThrow("boom");
    });

    act(() => result.current.clearError("occ-1"));

    expect(result.current.errors["occ-1"]).toBeUndefined();
  });
});
