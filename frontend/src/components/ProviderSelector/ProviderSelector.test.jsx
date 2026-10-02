import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ProviderSelector from "./ProviderSelector.jsx";

const PROVIDERS = [
  { provider: "groq", model: "llama", state: "healthy" },
  { provider: "euron", model: "gpt", state: "unavailable" },
];

describe("ProviderSelector", () => {
  it("offers Auto plus each configured provider", () => {
    render(<ProviderSelector providers={PROVIDERS} value="auto" onChange={vi.fn()} />);

    const options = screen.getAllByRole("option").map((option) => option.textContent);
    expect(options).toEqual(["Auto (Groq → Euron)", "Groq", "Euron (temporarily unavailable)"]);
  });

  it("reports the selected provider", async () => {
    const onChange = vi.fn();
    render(<ProviderSelector providers={PROVIDERS} value="auto" onChange={onChange} />);

    await userEvent.selectOptions(screen.getByLabelText("LLM"), "euron");

    expect(onChange).toHaveBeenCalledWith("euron");
  });
});
