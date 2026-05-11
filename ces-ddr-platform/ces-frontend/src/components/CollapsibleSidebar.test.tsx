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
  it("renders all 5 nav items by default", () => {
    renderSidebar();
    expect(screen.getByRole("link", { name: /Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /History/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Query/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Monitor/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Settings/i })).toBeInTheDocument();
  });

  it("collapses to icon-only when toggle button clicked", async () => {
    const user = userEvent.setup();
    renderSidebar();
    const toggle = screen.getByRole("button", { name: /Collapse sidebar/i });
    await user.click(toggle);
    expect(screen.getByRole("button", { name: /Expand sidebar/i })).toBeInTheDocument();
  });

  it("persists collapsed state to localStorage key ces-sidebar-collapsed", async () => {
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

  it("toggle button has correct aria-label based on state", async () => {
    const user = userEvent.setup();
    renderSidebar();
    expect(screen.getByRole("button", { name: "Collapse sidebar" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Collapse sidebar" }));
    expect(screen.getByRole("button", { name: "Expand sidebar" })).toBeInTheDocument();
  });
});
