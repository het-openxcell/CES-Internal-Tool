import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ReportsPage from "@/pages/ReportsPage";

const mockStatus = vi.fn();

vi.mock("@/hooks/useProcessingStatus", () => ({
  useProcessingStatus: (ddrId: string | undefined) => mockStatus(ddrId),
}));

function renderReportsPage(path = "/reports/ddr-1") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/reports/:id" element={<ReportsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ReportsPage", () => {
  beforeEach(() => {
    mockStatus.mockReturnValue({
      connectionMode: "sse",
      ddrStatus: "processing",
      rows: [
        { date: "20241031", status: "success" },
        { date: "20241101", status: "failed", error: "Tour Sheet Serial not detected" },
      ],
      successCount: 1,
      warningCount: 0,
      failedCount: 1,
      totalDates: 4,
      currentProcessedCount: 2,
      finalSummary: null,
      error: null,
    });
  });

  it("shows live processing copy and per-date counts", () => {
    renderReportsPage();

    expect(screen.getByText("Processing date 2 of 4...")).toBeInTheDocument();
    expect(screen.getByText("Success")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("Tour Sheet Serial not detected")).toBeInTheDocument();
  });

  it("replaces upload zone with progress while submitting", async () => {
    renderReportsPage();

    await userEvent.upload(screen.getByLabelText("Upload DDR PDF"), new File(["%PDF-1.7"], "field.pdf", { type: "application/pdf" }));

    expect(screen.queryByText("Drop DDR PDF here")).not.toBeInTheDocument();
    expect(screen.getByText("Uploading field.pdf")).toBeInTheDocument();
  });

  it("shows completion notification when processing finishes with failures", () => {
    mockStatus.mockReturnValue({
      connectionMode: "closed",
      ddrStatus: "complete",
      rows: [],
      successCount: 28,
      warningCount: 0,
      failedCount: 2,
      totalDates: 30,
      currentProcessedCount: 30,
      finalSummary: { total_dates: 30, failed_dates: 2, warning_dates: 0, total_occurrences: 0 },
      error: null,
    });

    renderReportsPage();

    expect(screen.getByText("Processing complete - 28 dates extracted, 2 failed")).toBeInTheDocument();
  });
});
