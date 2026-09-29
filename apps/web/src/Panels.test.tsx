import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { Leaderboard } from "./Panels";
import type { Run } from "./types";
it("renders measured metrics and visibly identifies the selected model", () => {
  const run = {
    leaderboard: [
      {
        model: "ridge",
        selected: true,
        selection_mae: 4,
        wape: 0.12,
        mase: null,
        rmse: 3,
        bias: -0.05,
        coverage_80: 0.75,
      },
    ],
  } as Run;
  render(<Leaderboard run={run} />);
  expect(screen.getByText("12.0%")).toBeInTheDocument();
  expect(screen.getByText("Selected")).toBeInTheDocument();
  expect(screen.getByText("—")).toBeInTheDocument();
  expect(screen.getByText("-5.0%")).toBeInTheDocument();
});
