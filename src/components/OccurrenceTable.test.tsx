import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import { OccurrenceTable } from "@/components/OccurrenceTable";
import type { OccurrenceRow } from "@/lib/api";

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
    ...overrides,
  };
}

function renderTable(props: Partial<React.ComponentProps<typeof OccurrenceTable>> = {}) {
  return render(
    <MemoryRouter>
      <OccurrenceTable occurrences={[]} failedDates={[]} isLoading={false} {...props} />
    </MemoryRouter>,
  );
}

describe("OccurrenceTable", () => {
  it("renders skeleton rows while loading", () => {
    renderTable({ isLoading: true });
    const rows = screen.getAllByRole("row");
    expect(rows.length).toBeGreaterThanOrEqual(5);
  });

  it("renders column headers", () => {
    renderTable();
    expect(screen.getByRole("columnheader", { name: /Well Name/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Surface Location/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Type/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Section/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /mMD/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Density/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Notes/i })).toBeInTheDocument();
  });

  it("renders empty state when no occurrences and not loading", () => {
    renderTable();
    expect(screen.getByText("No occurrences found for this DDR")).toBeInTheDocument();
  });

  it("renders occurrence row with TypeBadge", () => {
    renderTable({ occurrences: [makeOccurrence()] });
    expect(screen.getByLabelText("Stuck Pipe")).toBeInTheDocument();
  });

  it("renders SectionBadge with correct section label", () => {
    renderTable({ occurrences: [makeOccurrence()] });
    expect(screen.getByLabelText("Main")).toBeInTheDocument();
  });

  it("renders FailedDateRow with error message", () => {
    renderTable({
      occurrences: [],
      failedDates: [{ date: "20241101", error: "Tour Sheet Serial not detected" }],
    });
    expect(screen.getByText("Tour Sheet Serial not detected")).toBeInTheDocument();
    expect(screen.getByLabelText("Date resolution failed. Action required.")).toBeInTheDocument();
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
        makeOccurrence({ id: "occ-2", well_name: "Duvernay B" }),
      ],
    });

    const search = screen.getByLabelText("Search occurrences");
    await user.type(search, "Duvernay");

    const tableBody = screen.getByRole("grid").querySelector("tbody")!;
    expect(within(tableBody).queryByText("Montney A")).not.toBeInTheDocument();
    expect(within(tableBody).getByText("Duvernay B")).toBeInTheDocument();
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
      failedDates: [{ date: "20241101", error: "fail" }],
    });

    const grid = screen.getByRole("grid");
    expect(grid).toHaveAttribute("aria-rowcount", "2");
  });

  it("sorts by column header click cycling asc desc unsorted", async () => {
    const user = userEvent.setup();
    renderTable({
      occurrences: [
        makeOccurrence({ id: "a", well_name: "Alpha" }),
        makeOccurrence({ id: "b", well_name: "Beta" }),
      ],
    });

    const wellHeader = screen.getByRole("columnheader", { name: /Well Name/i });
    await user.click(wellHeader);
    expect(wellHeader).toHaveAttribute("aria-sort", "ascending");

    await user.click(wellHeader);
    expect(wellHeader).toHaveAttribute("aria-sort", "descending");

    await user.click(wellHeader);
    expect(wellHeader).toHaveAttribute("aria-sort", "none");
  });

  it("renders em dash for null well_name and notes", () => {
    renderTable({
      occurrences: [makeOccurrence({ well_name: null, notes: null })],
    });
    const grid = screen.getByRole("grid");
    const cells = within(grid).getAllByRole("gridcell");
    expect(cells.some((c) => c.textContent === "—")).toBe(true);
  });
});
