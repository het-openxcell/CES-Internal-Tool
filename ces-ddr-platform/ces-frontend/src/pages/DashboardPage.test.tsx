import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/pages/DashboardPage";

class FakeXMLHttpRequest {
  static instances: FakeXMLHttpRequest[] = [];
  upload = { onprogress: null as ((event: ProgressEvent) => void) | null };
  status = 201;
  responseText = JSON.stringify({ id: "new-ddr", status: "queued" });
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  open = vi.fn();
  setRequestHeader = vi.fn();

  constructor() {
    FakeXMLHttpRequest.instances.push(this);
  }

  send() {
    this.upload.onprogress?.({ lengthComputable: true, loaded: 50, total: 100 } as ProgressEvent);
    this.onload?.();
  }
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    FakeXMLHttpRequest.instances = [];
    vi.stubGlobal("XMLHttpRequest", FakeXMLHttpRequest);
  });

  it("redirects to first report when reports exist", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify([
          { id: "ddr-1", file_path: "/uploads/field-1.pdf", status: "processing", created_at: 1778158800 },
          { id: "ddr-2", file_path: "/uploads/field-2.pdf", status: "complete", created_at: 1778072400 },
        ]),
        { status: 200 },
      ),
    );

    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/reports/:id" element={<h1>Report Detail</h1>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Report Detail" })).toBeInTheDocument();
  });

  it("shows empty state when there are no DDRs", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("No reports yet")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "DDR Processing" })).toBeInTheDocument();
  });
});
