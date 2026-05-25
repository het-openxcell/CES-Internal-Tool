import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { OccurrenceTable } from "@/components/OccurrenceTable";
import { apiClient, type OccurrenceRow } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      patchOccurrence: vi.fn(),
    },
  };
});

const patchOccurrence = vi.mocked(apiClient.patchOccurrence);

function makeOccurrence(overrides: Partial<OccurrenceRow> = {}): OccurrenceRow {
  return {
    id: "occ-1",
    ddr_id: "ddr-1",
    well_name: "Montney A",
    surface_location: null,
    type: "Stuck Pipe",
    section: "Main",
    mmd: 2100.0,
    density: 1.35,
    notes: "pipe stuck after connection",
    date: "20241031",
    page_number: null,
    ...overrides,
  };
}

function renderTable(props: Partial<React.ComponentProps<typeof OccurrenceTable>> = {}) {
  return render(
    <MemoryRouter>
      <OccurrenceTable occurrences={[]} isLoading={false} {...props} />
    </MemoryRouter>,
  );
}

describe("OccurrenceTable", () => {
  beforeEach(() => {
    patchOccurrence.mockReset();
  });
  it("renders skeleton rows while loading", () => {
    renderTable({ isLoading: true });
    const rows = screen.getAllByRole("row");
    expect(rows.length).toBeGreaterThanOrEqual(5);
  });

  it("renders column headers", () => {
    renderTable();
    expect(screen.getByRole("columnheader", { name: /Edited/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Incident Date/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Well Name/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Type/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Section/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /mMD/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Density/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Surface Location/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Notes/i })).toBeInTheDocument();
  });

  it("renders empty state when no occurrences and not loading", () => {
    renderTable();
    expect(screen.getByText("No occurrences found for this DDR")).toBeInTheDocument();
  });

  it("formats compact incident dates", () => {
    renderTable({ occurrences: [makeOccurrence()] });
    expect(screen.getByText("10/31/2024")).toBeInTheDocument();
  });

  it("renders occurrence row with TypeBadge", () => {
    renderTable({ occurrences: [makeOccurrence()] });
    expect(screen.getByLabelText("Stuck Pipe")).toBeInTheDocument();
  });

  it("renders SectionBadge with correct section label", () => {
    renderTable({ occurrences: [makeOccurrence()] });
    expect(screen.getByLabelText("Main")).toBeInTheDocument();
  });

  it("filters rows by type dropdown", async () => {
    const user = userEvent.setup();
    renderTable({
      occurrences: [makeOccurrence(), makeOccurrence({ id: "occ-2", type: "Washout" })],
    });

    const typeSelect = screen.getByLabelText("Filter by type");
    await user.selectOptions(typeSelect, "Washout");

    const tableBody = screen.getByRole("grid").querySelector("tbody")!;
    expect(within(tableBody).queryByLabelText("Stuck Pipe")).not.toBeInTheDocument();
    expect(within(tableBody).getByLabelText("Washout")).toBeInTheDocument();
  });

  it("filters rows by section dropdown", async () => {
    const user = userEvent.setup();
    renderTable({
      occurrences: [makeOccurrence(), makeOccurrence({ id: "occ-2", section: "Surface" })],
    });

    const sectionSelect = screen.getByLabelText("Filter by section");
    await user.selectOptions(sectionSelect, "Surface");

    const tableBody = screen.getByRole("grid").querySelector("tbody")!;
    expect(within(tableBody).queryByLabelText("Main")).not.toBeInTheDocument();
    expect(within(tableBody).getByLabelText("Surface")).toBeInTheDocument();
  });

  it("global text search filters rows", async () => {
    const user = userEvent.setup();
    renderTable({
      occurrences: [
        makeOccurrence(),
        makeOccurrence({ id: "occ-2", notes: "Duvernay observation" }),
      ],
    });

    const search = screen.getByLabelText("Search occurrences");
    await user.type(search, "Duvernay");

    const tableBody = screen.getByRole("grid").querySelector("tbody")!;
    expect(within(tableBody).queryByText("pipe stuck after connection")).not.toBeInTheDocument();
    expect(within(tableBody).getByText("Duvernay observation")).toBeInTheDocument();
  });

  it("active filter shows as pill chip with x button", async () => {
    const user = userEvent.setup();
    renderTable({
      occurrences: [makeOccurrence()],
    });

    const typeSelect = screen.getByLabelText("Filter by type");
    await user.selectOptions(typeSelect, "Stuck Pipe");

    const chip = screen.getByText(/Type: Stuck Pipe/);
    expect(chip).toBeInTheDocument();
    expect(within(chip.closest("span")!).getByRole("button", { name: /Remove/i })).toBeInTheDocument();
  });

  it("clicking x on filter chip clears that filter", async () => {
    const user = userEvent.setup();
    renderTable({
      occurrences: [makeOccurrence()],
    });

    const typeSelect = screen.getByLabelText("Filter by type");
    await user.selectOptions(typeSelect, "Stuck Pipe");

    const chip = screen.getByText(/Type: Stuck Pipe/);
    const removeBtn = within(chip.closest("span")!).getByRole("button", { name: /Remove/i });
    await user.click(removeBtn);

    expect(screen.queryByText(/Type: Stuck Pipe/)).not.toBeInTheDocument();
  });

  it("table has role=grid and aria-rowcount attribute", () => {
    renderTable({
      occurrences: [makeOccurrence()],
    });

    const grid = screen.getByRole("grid");
    expect(grid).toHaveAttribute("aria-rowcount", "1");
  });

  it("sorts by column header click cycling asc desc unsorted", async () => {
    const user = userEvent.setup();
    renderTable({
      occurrences: [
        makeOccurrence({ id: "a", type: "Alpha" }),
        makeOccurrence({ id: "b", type: "Beta" }),
      ],
    });

    const typeHeader = screen.getByRole("columnheader", { name: /Type/i });
    await user.click(typeHeader);
    expect(typeHeader).toHaveAttribute("aria-sort", "ascending");

    await user.click(typeHeader);
    expect(typeHeader).toHaveAttribute("aria-sort", "descending");

    await user.click(typeHeader);
    expect(typeHeader).toHaveAttribute("aria-sort", "none");
  });

  it("renders em dash for null notes", () => {
    renderTable({
      occurrences: [makeOccurrence({ notes: null })],
    });
    const grid = screen.getByRole("grid");
    const cells = within(grid).getAllByRole("gridcell");
    expect(cells.some((c) => c.textContent === "—")).toBe(true);
  });

  it("opens type dropdown on one click but ignores read-only cells", async () => {
    const user = userEvent.setup();
    renderTable({ occurrences: [makeOccurrence()] });

    await user.click(screen.getByText("Montney A"));
    expect(screen.queryByLabelText("Edit Type")).not.toBeInTheDocument();

    await user.click(screen.getByText("10/31/2024"));
    expect(screen.queryByLabelText("Edit Type")).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("Stuck Pipe"));

    expect(screen.getByLabelText("Edit Type")).toHaveFocus();
    expect(screen.getByRole("button", { name: "Stuck Pipe" })).toBeInTheDocument();
  });

  it("selecting a new type opens reason modal with autofocus", async () => {
    const user = userEvent.setup();
    renderTable({ occurrences: [makeOccurrence()] });

    await user.click(screen.getByLabelText("Stuck Pipe"));
    await user.click(screen.getByRole("button", { name: "Washout" }));

    expect(screen.getByRole("dialog", { name: "Reason for correction" })).toBeInTheDocument();
    expect(screen.getByText("Type: Stuck Pipe → Washout")).toBeInTheDocument();
    expect(screen.getByLabelText("Why was this changed?")).toHaveFocus();
  });

  it("saves type correction, shows edited dot, and displays success toast", async () => {
    const user = userEvent.setup();
    patchOccurrence.mockResolvedValue(makeOccurrence({ type: "Washout" }));
    renderTable({ occurrences: [makeOccurrence()] });

    await user.click(screen.getByLabelText("Stuck Pipe"));
    await user.click(screen.getByRole("button", { name: "Washout" }));
    await user.type(screen.getByLabelText("Why was this changed?"), "field verified{Enter}");

    await waitFor(() => {
      expect(patchOccurrence).toHaveBeenCalledWith("occ-1", "type", "Washout", "field verified");
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Cell manually corrected")).toBeInTheDocument();
    expect(screen.getByText("Correction saved — will inform future extractions")).toBeInTheDocument();
  });

  it("Escape cancels the reason modal without saving or leaving edited value", async () => {
    const user = userEvent.setup();
    renderTable({ occurrences: [makeOccurrence()] });

    await user.click(screen.getByLabelText("Stuck Pipe"));
    await user.click(screen.getByRole("button", { name: "Washout" }));
    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(patchOccurrence).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Stuck Pipe")).toBeInTheDocument();
    expect(screen.queryByLabelText("Washout")).not.toBeInTheDocument();
  });

  it("shows row error and reverts when correction save fails", async () => {
    const user = userEvent.setup();
    patchOccurrence.mockRejectedValue(new Error("save failed"));
    renderTable({ occurrences: [makeOccurrence()] });

    await user.click(screen.getByLabelText("Stuck Pipe"));
    await user.click(screen.getByRole("button", { name: "Washout" }));
    await user.type(screen.getByLabelText("Why was this changed?"), "wrong type{Enter}");

    await waitFor(() => {
      expect(screen.getByText("Couldn't save correction — try again")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Stuck Pipe")).toBeInTheDocument();
    expect(screen.queryByText("Correction saved — will inform future extractions")).not.toBeInTheDocument();
  });

  it("opens a full notes editor so long notes are readable before saving", async () => {
    const user = userEvent.setup();
    patchOccurrence.mockResolvedValue(makeOccurrence({ notes: "updated full notes" }));
    renderTable({ occurrences: [makeOccurrence()] });

    await user.click(screen.getByText("pipe stuck after connection"));

    expect(screen.getByRole("dialog", { name: "Edit notes" })).toBeInTheDocument();
    const notesEditor = screen.getByDisplayValue("pipe stuck after connection");
    expect(notesEditor.tagName).toBe("TEXTAREA");

    await user.clear(notesEditor);
    await user.type(notesEditor, "updated full notes with more context");
    await user.type(screen.getByPlaceholderText("Why was this changed?"), "field note corrected");
    await user.click(screen.getByRole("button", { name: "Save correction" }));

    await waitFor(() => {
      expect(patchOccurrence).toHaveBeenCalledWith("occ-1", "notes", "updated full notes with more context", "field note corrected");
    });
    expect(screen.queryByRole("dialog", { name: "Edit notes" })).not.toBeInTheDocument();
  });
});
