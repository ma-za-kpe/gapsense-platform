import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AssessmentPlanner } from "./AssessmentPlanner";
import { sampleDraftStorageKey } from "../domain/sampleDraft";
import type { AnalyticsEventName } from "../analytics/client";

afterEach(() => {
  window.localStorage.clear();
});

describe("resumable public sample planner", () => {
  it("restores intent while distinguishing the available practice sample from future workflows", async () => {
    const user = userEvent.setup();
    const onOpenAssessment = vi.fn();
    render(
      <AssessmentPlanner
        analytics={{ track: vi.fn() }}
        onOpenAssessment={onOpenAssessment}
        storage={window.localStorage}
      />,
    );

    expect(screen.getByRole("group", { name: /Who will use the sample/ })).toBeVisible();
    expect(screen.getByRole("group", { name: /Choose an illustrative context/ })).toBeVisible();
    expect(screen.getByRole("group", { name: /What should this help you do/ })).toBeVisible();
    expect(screen.getByRole("radio", { name: /^Practice activity/ })).toBeEnabled();
    expect(screen.getByRole("radio", { name: /^Diagnostic pathway/ })).toBeDisabled();
    expect(screen.getByRole("radio", { name: /^Assessment package/ })).toBeDisabled();
    expect(screen.getByText("In development")).toBeVisible();
    expect(screen.getByText("Requires reviewed evidence")).toBeVisible();
    const review = screen.getByRole("button", { name: "Review sample choice" });
    expect(review).toBeDisabled();
    const form = review.closest("form");
    if (form === null) throw new Error("Sample review form was not rendered");
    fireEvent.submit(form);

    await user.click(screen.getByRole("radio", { name: /^Teacher/ }));
    await user.click(screen.getByRole("radio", { name: /^Ghana/ }));
    expect(review).toBeDisabled();
    await user.click(screen.getByRole("radio", { name: /^Practice activity/ }));
    expect(review).toBeEnabled();
    await user.click(review);

    expect(
      screen.getByRole("heading", { level: 3, name: "Your Ghana sample is ready" }),
    ).toBeVisible();
    expect(screen.getAllByText(/Basic 3 Science/).length).toBeGreaterThan(0);
    expect(screen.getByText("Teacher · Practice activity")).toBeVisible();
    expect(
      screen.getAllByText(/not curriculum-aligned or educator-reviewed/i).length,
    ).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: "Open sample activity" }));
    expect(onOpenAssessment).toHaveBeenCalledOnce();
  });

  it("restores an interrupted non-PII choice and supports a safe reset", async () => {
    const user = userEvent.setup();
    const first = render(
      <AssessmentPlanner
        analytics={{ track: vi.fn() }}
        onOpenAssessment={vi.fn()}
        storage={window.localStorage}
      />,
    );
    await user.click(screen.getByRole("radio", { name: /^Tutor/ }));
    await user.click(screen.getByRole("radio", { name: /^Uganda/ }));
    await user.click(screen.getByRole("radio", { name: /^Practice activity/ }));
    await user.click(screen.getByRole("button", { name: "Review sample choice" }));
    await waitFor(() => expect(window.localStorage.getItem(sampleDraftStorageKey)).not.toBeNull());
    first.unmount();

    render(
      <AssessmentPlanner
        analytics={{ track: vi.fn() }}
        onOpenAssessment={vi.fn()}
        storage={window.localStorage}
      />,
    );
    expect(screen.getByRole("radio", { name: /^Tutor/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /^Uganda/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /^Practice activity/ })).toBeChecked();
    expect(screen.getByRole("status")).toHaveTextContent("Restored your saved sample choice");
    await user.click(screen.getByRole("button", { name: "Start again" }));
    expect(window.localStorage.getItem(sampleDraftStorageKey)).toBeNull();
    expect(screen.getByRole("button", { name: "Review sample choice" })).toBeDisabled();
  });

  it("explains discarded or unavailable storage without blocking the sample", () => {
    window.localStorage.setItem(sampleDraftStorageKey, "{broken");
    const { unmount } = render(
      <AssessmentPlanner
        analytics={{ track: vi.fn() }}
        onOpenAssessment={vi.fn()}
        storage={window.localStorage}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "A saved choice could not be restored and was safely cleared",
    );
    unmount();

    const unavailableStorage = {
      getItem: vi.fn(() => {
        throw new DOMException("blocked");
      }),
      setItem: vi.fn(() => {
        throw new DOMException("blocked");
      }),
      removeItem: vi.fn(() => {
        throw new DOMException("blocked");
      }),
    };
    render(
      <AssessmentPlanner
        analytics={{ track: vi.fn() }}
        onOpenAssessment={vi.fn()}
        storage={unavailableStorage}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "This browser cannot save your choice; keep this tab open",
    );
  });

  it("records only allowlisted action names, never selected values", async () => {
    const events: AnalyticsEventName[] = [];
    const user = userEvent.setup();
    render(
      <AssessmentPlanner
        analytics={{ track: (event) => events.push(event) }}
        onOpenAssessment={vi.fn()}
        storage={window.localStorage}
      />,
    );

    await user.click(screen.getByRole("radio", { name: /^Learner/ }));
    await user.click(screen.getByRole("radio", { name: /^Uganda/ }));
    await user.click(screen.getByRole("radio", { name: /^Practice activity/ }));
    await user.click(screen.getByRole("button", { name: "Review sample choice" }));
    await user.click(screen.getByRole("button", { name: "Open sample activity" }));
    await user.click(screen.getByRole("button", { name: "Start again" }));

    expect(events).toEqual([
      "planner_role_selected",
      "planner_country_selected",
      "planner_goal_selected",
      "planner_reviewed",
      "sample_opened",
      "planner_reset",
    ]);
    expect(JSON.stringify(events)).not.toMatch(/learner|uganda/i);
  });

  it("keeps working and explains when a new choice cannot be saved", async () => {
    const user = userEvent.setup();
    const onOpenAssessment = vi.fn();
    const storage = {
      getItem: vi.fn(() => null),
      setItem: vi.fn(() => {
        throw new DOMException("full");
      }),
      removeItem: vi.fn(),
    };
    render(
      <AssessmentPlanner
        analytics={{ track: vi.fn() }}
        onOpenAssessment={onOpenAssessment}
        storage={storage}
      />,
    );

    await user.click(screen.getByRole("radio", { name: /^Teacher/ }));
    await user.click(screen.getByRole("radio", { name: /^Ghana/ }));
    await user.click(screen.getByRole("radio", { name: /^Practice activity/ }));
    await user.click(screen.getByRole("button", { name: "Review sample choice" }));
    await user.click(screen.getByRole("button", { name: "Open sample activity" }));

    expect(screen.getByRole("status")).toHaveTextContent(
      "This browser cannot save your choice; keep this tab open",
    );
    expect(onOpenAssessment).toHaveBeenCalledOnce();
  });
});
