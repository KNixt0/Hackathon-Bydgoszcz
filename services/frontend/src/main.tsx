import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-ext-400.css";
import "@fontsource/ibm-plex-sans/latin-500.css";
import "@fontsource/ibm-plex-sans/latin-ext-500.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "@fontsource/ibm-plex-sans/latin-ext-600.css";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/ui.css";
import "./styles/layout.css";
import "./styles/queue.css";
import "./styles/calibration.css";
import "./styles/case.css";
import "./styles/auth.css";
import "./styles/report.css";
import { App } from "./App";

const container = document.getElementById("root");
if (container) {
  // Render errors are shown by the ErrorBoundary; the handlers below keep them out of the console.
  const silent = () => undefined;
  createRoot(container, { onCaughtError: silent, onUncaughtError: silent, onRecoverableError: silent }).render(
    <StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </StrictMode>,
  );
}
