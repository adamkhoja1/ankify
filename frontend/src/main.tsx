import React from "react";
import { createRoot } from "react-dom/client";
import { MathJaxContext } from "better-react-mathjax";
import App from "./App";
import "./styles.css";

// Only \(...\) and \[...\] are math (matching Anki's MathJax). `$`/`$$` are NOT delimiters,
// so dollar amounts in text (e.g. "$4 latte") don't get mis-rendered as math.
const mathJaxConfig = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
  },
  options: { enableMenu: false },
};

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MathJaxContext version={3} config={mathJaxConfig}>
      <App />
    </MathJaxContext>
  </React.StrictMode>,
);
