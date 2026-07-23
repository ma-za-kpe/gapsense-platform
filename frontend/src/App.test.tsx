import axe from "axe-core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const readyResponse = () =>
  new Response(JSON.stringify({ status: "ready", checks: { curriculum_data: "ready" } }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });

const renderReadyApp = () => {
  vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(readyResponse()));
  return render(<App />);
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("GapSense web entry experience", () => {
  it("introduces both countries and reports connected local evidence", async () => {
    renderReadyApp();

    expect(
      screen.getByRole("heading", { level: 1, name: "Find the next learning step." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Ghana" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Uganda" })).toBeInTheDocument();
    expect(screen.getByText("No account. No learner data. No hidden AI dependency.")).toBeVisible();
    expect(await screen.findByText("Curriculum evidence connected")).toBeVisible();
  });

  it("uses Maku's Africa-first attribution without institutional branding", async () => {
    const { container } = renderReadyApp();

    expect(await screen.findByText("Curriculum evidence connected")).toBeVisible();
    expect(screen.getByText("Built by Maku for Africa.")).toBeVisible();
    expect(
      screen.getByText("Built by Maku for Africa, grounded first in Ghana and Uganda."),
    ).toBeVisible();
    expect(container).not.toHaveTextContent(/UNICEF/i);
  });

  it("keeps planning available when the API is unavailable and recovers on retry", async () => {
    const user = userEvent.setup();
    const fetcher = vi
      .fn<typeof fetch>()
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockResolvedValueOnce(readyResponse());
    vi.stubGlobal("fetch", fetcher);
    render(<App />);

    expect(await screen.findByText("Planning still works locally")).toBeVisible();
    const retry = screen.getByRole("button", { name: "Check connection again" });
    await user.click(retry);

    expect(await screen.findByText("Curriculum evidence connected")).toBeVisible();
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("builds and resets an honest Ghana starting point", async () => {
    const user = userEvent.setup();
    renderReadyApp();

    const reviewButton = screen.getByRole("button", { name: "Review my starting point" });
    expect(reviewButton).toBeDisabled();

    await user.click(screen.getByRole("radio", { name: /^Teacher/ }));
    await user.click(screen.getByRole("radio", { name: /^Ghana/ }));
    await user.click(screen.getByRole("radio", { name: /^Diagnostic check/ }));
    expect(reviewButton).toBeEnabled();
    await user.click(reviewButton);

    expect(
      screen.getByRole("heading", { level: 3, name: "Your Ghana starting point is ready" }),
    ).toBeVisible();
    expect(screen.getByText("Teacher · Diagnostic check")).toBeVisible();
    expect(screen.getByText(/NaCCA curriculum inventory is still being verified/)).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Start again" }));
    expect(screen.queryByText("Your Ghana starting point is ready")).not.toBeInTheDocument();
    expect(reviewButton).toBeDisabled();
  });

  it("uses Uganda-specific terminology in the reviewed plan", async () => {
    const user = userEvent.setup();
    renderReadyApp();

    await user.click(screen.getByRole("radio", { name: /^Parent or caregiver/ }));
    await user.click(screen.getByRole("radio", { name: /^Uganda/ }));
    await user.click(screen.getByRole("radio", { name: /^Practice activity/ }));
    await user.click(screen.getByRole("button", { name: "Review my starting point" }));

    expect(
      screen.getByRole("heading", { level: 3, name: "Your Uganda starting point is ready" }),
    ).toBeVisible();
    expect(screen.getByText("Parent or caregiver · Practice activity")).toBeVisible();
    expect(screen.getByText(/NCDC curriculum inventory is still being verified/)).toBeVisible();
  });

  it("has no automatically detectable document-level accessibility violations", async () => {
    const { container } = renderReadyApp();
    await screen.findByText("Curriculum evidence connected");

    const results = await axe.run(container, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"] },
    });

    expect(results.violations).toEqual([]);
  });
});
