import { act } from "react";
import { waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  document.body.innerHTML = "";
  vi.resetModules();
  vi.unstubAllGlobals();
});

describe("application bootstrap", () => {
  it("mounts GapSense into the required root", async () => {
    document.body.innerHTML = '<div id="root"></div>';
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockRejectedValue(new TypeError("offline")));

    const module = await act(async () => import("./main"));
    await waitFor(() => {
      expect(document.querySelector("h1")).toHaveTextContent("Find the next learning step.");
    });

    act(() => {
      module.appRoot.unmount();
    });
  });

  it("fails clearly when the root container is missing", async () => {
    await expect(import("./main")).rejects.toThrow("GapSense root element was not found");
  });
});
