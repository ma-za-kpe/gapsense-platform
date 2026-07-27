import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AssessmentWorkspace } from "./AssessmentWorkspace";
import { saveSampleDraft, sampleDraftStorageKey } from "../domain/sampleDraft";

afterEach(() => {
  window.localStorage.clear();
  Reflect.deleteProperty(navigator, "share");
  Reflect.deleteProperty(navigator, "clipboard");
});

const saveTeacherGhanaDraft = () => {
  saveSampleDraft(window.localStorage, {
    role: "teacher",
    country: "ghana",
    goal: "practice",
    reviewed: true,
  });
};

describe("focused sample activity workspace", () => {
  it("shows a recoverable empty state when no reviewed draft exists", () => {
    render(<AssessmentWorkspace onReturnHome={vi.fn()} storage={window.localStorage} />);

    expect(
      screen.getByRole("heading", { level: 1, name: "No saved sample activity" }),
    ).toBeVisible();
    expect(
      screen.getByText(/Choose a role, one illustrative country context, and an available purpose/),
    ).toBeVisible();
  });

  it("keeps learner and answer artifacts separate and labels every action precisely", async () => {
    saveTeacherGhanaDraft();
    const user = userEvent.setup();
    const createObjectURL = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:sample");
    const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
    render(<AssessmentWorkspace onReturnHome={vi.fn()} storage={window.localStorage} />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Ghana Basic 3 Science sample" }),
    ).toBeVisible();
    expect(screen.getByText(/For classroom exploration/)).toBeVisible();
    expect(
      screen.getAllByText(/not curriculum-aligned or educator-reviewed/i).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("Name one source of light.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Trace curriculum" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Download learner worksheet" }));
    await user.click(screen.getByRole("button", { name: "Download answer guide" }));
    expect(createObjectURL).toHaveBeenCalledTimes(2);
    expect(click).toHaveBeenCalledTimes(2);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:sample");
    await user.click(screen.getByRole("button", { name: "Print learner worksheet" }));
    expect(print).toHaveBeenCalledOnce();
    await user.click(screen.getByText("Show answer guidance"));
    expect(screen.getByText(/sun, a lamp/i)).toBeVisible();

    click.mockRestore();
    createObjectURL.mockRestore();
    revokeObjectURL.mockRestore();
    print.mockRestore();
  });

  it("reports share success, cancellation, unavailable APIs, and clipboard failure", async () => {
    saveTeacherGhanaDraft();
    const user = userEvent.setup();
    const share = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "share", { configurable: true, value: share });
    const view = render(
      <AssessmentWorkspace onReturnHome={vi.fn()} storage={window.localStorage} />,
    );
    await user.click(screen.getByRole("button", { name: "Share sample summary" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Share sheet opened");

    Object.defineProperty(navigator, "share", {
      configurable: true,
      value: vi.fn().mockRejectedValue(new Error("cancelled")),
    });
    await user.click(screen.getByRole("button", { name: "Share sample summary" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Sharing did not finish. Download the activity instead",
    );
    Reflect.deleteProperty(navigator, "share");
    await user.click(screen.getByRole("button", { name: "Share sample summary" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Sharing is unavailable. Copy the summary or download the activity instead",
    );
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
    await user.click(screen.getByRole("button", { name: "Copy summary" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Summary copied");

    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
    });
    await user.click(screen.getByRole("button", { name: "Copy summary" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Copying is unavailable. Download the activity instead",
    );
    Reflect.deleteProperty(navigator, "clipboard");
    await user.click(screen.getByRole("button", { name: "Copy summary" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Copying is unavailable. Download the activity instead",
    );
    view.unmount();
  });

  it("clears the saved draft before returning home", async () => {
    saveTeacherGhanaDraft();
    const onReturnHome = vi.fn();
    const user = userEvent.setup();
    render(<AssessmentWorkspace onReturnHome={onReturnHome} storage={window.localStorage} />);

    await user.click(screen.getByRole("button", { name: "Choose another sample" }));

    expect(window.localStorage.getItem(sampleDraftStorageKey)).toBeNull();
    expect(onReturnHome).toHaveBeenCalledOnce();
  });

  it("fails closed when a saved record becomes invalid", async () => {
    window.localStorage.setItem(
      sampleDraftStorageKey,
      '{"version":1,"role":"teacher","country":"ghana","reviewed":false}',
    );
    render(<AssessmentWorkspace onReturnHome={vi.fn()} storage={window.localStorage} />);

    await waitFor(() =>
      expect(
        screen.getByRole("heading", { level: 1, name: "No saved sample activity" }),
      ).toBeVisible(),
    );
  });
});
