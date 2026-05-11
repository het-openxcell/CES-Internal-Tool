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

  it("renders DDR work instead of scaffold copy", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify([
          { id: "ddr-1", file_path: "/uploads/field-1.pdf", status: "processing", created_at: 1778158800 },
          { id: "ddr-2", file_path: "/uploads/field-2.pdf", status: "complete", created_at: 1778072400 },
          { id: "ddr-3", file_path: "/uploads/field-3.pdf", status: "failed", created_at: 1777986000 },
        ]),
        { status: 200 },
      ),
    );

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText("field-1.pdf")).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "DDR Processing" })).toBeInTheDocument();
    expect(screen.getByLabelText("DDR queue summary")).toHaveTextContent("Active DDRs1");
    expect(screen.getByLabelText("Recent DDRs")).toHaveTextContent("3 DDRs");
    expect(screen.getByLabelText("Recent DDRs")).toHaveTextContent("1 active, 1 complete, 1 failed");
    expect(screen.queryByText("Local scaffold")).not.toBeInTheDocument();
    expect(screen.queryByText("Extraction and reporting foundation")).not.toBeInTheDocument();
    expect(screen.queryByText("DDR extraction work")).not.toBeInTheDocument();
  });

  it("shows upload action when there are no DDRs", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("No DDRs uploaded yet")).toBeInTheDocument();
    expect(screen.getByLabelText("Recent DDRs")).toHaveTextContent("No DDRs uploaded");
    expect(screen.getAllByText("Upload DDR PDF").length).toBeGreaterThan(0);
  });

  it("uploads a DDR from the dashboard and opens the created report", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));

    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/reports/:id" element={<h1>Created report</h1>} />
        </Routes>
      </MemoryRouter>,
    );

    await screen.findByText("No DDRs uploaded yet");
    await userEvent.upload(
      screen.getAllByLabelText("Upload DDR PDF")[0],
      new File(["%PDF-1.7"], "field.pdf", { type: "application/pdf" }),
    );

    expect(await screen.findByRole("heading", { name: "Created report" })).toBeInTheDocument();
    expect(FakeXMLHttpRequest.instances[0].open).toHaveBeenCalledWith("POST", "https://ces-backend.apps.openxcell.dev/api/ddrs/upload");
  });
});
