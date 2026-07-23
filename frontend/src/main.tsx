import { StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";

import { App } from "./App";

export function bootstrap(container: HTMLElement | null): Root {
  if (container === null) {
    throw new Error("GapSense root element was not found");
  }

  const root = createRoot(container);
  root.render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
  return root;
}

export const appRoot = bootstrap(document.getElementById("root"));
