import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ModeSelector from "./ModeSelector.jsx";

const MODES = [
  { key: "learning", name: "Learning", description: "Fundamentals first" },
  { key: "interview", name: "Interview", description: "Interview-ready" },
];

describe("ModeSelector", () => {
  it("calls onChange with the selected mode key", async () => {
    const onChange = vi.fn();
    render(<ModeSelector modes={MODES} value="learning" onChange={onChange} />);

    await userEvent.selectOptions(screen.getByLabelText("Mode"), "interview");

    expect(onChange).toHaveBeenCalledWith("interview");
  });
});
