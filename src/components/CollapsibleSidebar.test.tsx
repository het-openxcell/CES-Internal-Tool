import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import CollapsibleSidebar from "@/components/CollapsibleSidebar";

function renderSidebar() {
  return render(
    <MemoryRouter>
      <CollapsibleSidebar />
    </MemoryRouter>,
  );
}

describe("CollapsibleSidebar", () => {
  it("renders collapse toggle by default", () => {
    renderSidebar();
    expect(screen.getByRole("button", { name: /Collapse sidebar/i })).toBeInTheDocument();
  });

  it("collapses when toggle button clicked", async () => {
    const user = userEvent.setup();
    renderSidebar();
    const toggle = screen.getByRole("button", { name: /Collapse sidebar/i });
    await user.click(toggle);
    expect(screen.getByRole("button", { name: /Expand sidebar/i })).toBeInTheDocument();
  });

  it("persists collapsed state to localStorage", async () => {
    const user = userEvent.setup();
    renderSidebar();
    const toggle = screen.getByRole("button", { name: /Collapse sidebar/i });
    await user.click(toggle);
    expect(localStorage.getItem("ces-sidebar-collapsed")).toBe("true");
  });

  it("restores collapsed state from localStorage on mount", () => {
    localStorage.setItem("ces-sidebar-collapsed", "true");
    renderSidebar();
    expect(screen.getByRole("button", { name: /Expand sidebar/i })).toBeInTheDocument();
  });
});
