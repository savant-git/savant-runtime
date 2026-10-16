import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
vi.mock("./cinematic/CinematicIntro", () => ({
  default: () => <div data-testid="intro" />,
}));
import { App } from "./App";
describe("application route persistence", () => {
  beforeEach(() => sessionStorage.clear());
  afterEach(cleanup);
  it("loads the site concurrently behind the intro", async () => {
    render(<App />);
    expect(screen.getByRole("main", { hidden: true })).toBeInTheDocument();
    expect(await screen.findByTestId("intro")).toBeInTheDocument();
  });
  it("does not replay after entered state is persisted", () => {
    sessionStorage.setItem("savant-entered", "true");
    render(<App />);
    expect(screen.queryByTestId("intro")).not.toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveClass("site--entered");
  });
});
