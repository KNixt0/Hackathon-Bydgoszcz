import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { RuleTip } from "../../src/components/ui/RuleTip";

describe("criterion definition", () => {
  it("supports keyboard focus, Escape and a single touch/click", async () => {
    const user = userEvent.setup(); render(<RuleTip id="3" />);
    await user.tab();
    expect(screen.getByRole("tooltip")).toHaveTextContent("Informacja o ryzyku");
    await user.keyboard("{Escape}"); expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button")); expect(screen.getByRole("tooltip")).toBeInTheDocument();
    await user.click(document.body); await waitFor(() => expect(screen.queryByRole("tooltip")).not.toBeInTheDocument());
  });
});
