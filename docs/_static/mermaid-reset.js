document.addEventListener("DOMContentLoaded", () => {
  const isDarkTheme = () => {
    if (
      document.documentElement.classList.contains("dark") ||
      document.documentElement.getAttribute("data-theme") === "dark" ||
      document.body.classList.contains("dark") ||
      document.body.getAttribute("data-theme") === "dark"
    ) {
      return true;
    }
    if (
      document.documentElement.classList.contains("light") ||
      document.documentElement.getAttribute("data-theme") === "light" ||
      document.body.classList.contains("light") ||
      document.body.getAttribute("data-theme") === "light"
    ) {
      return false;
    }
    if (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    ) {
      return true;
    }
    const bgColor = window.getComputedStyle(document.body).backgroundColor;
    const match = bgColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)/);
    if (match) {
      const r = parseInt(match[1]);
      const g = parseInt(match[2]);
      const b = parseInt(match[3]);
      const brightness = (r * 299 + g * 587 + b * 114) / 1000;
      return brightness < 128;
    }
    return false;
  };

  const addResetButtons = () => {
    document.querySelectorAll(".mermaid").forEach((diagram) => {
      if (diagram.querySelector(".reset-zoom-btn")) return;
      const svg = diagram.querySelector("svg");
      if (!svg) return;
      const resetBtn = document.createElement("button");
      resetBtn.className = "reset-zoom-btn";
      const darkMode = isDarkTheme();
      if (darkMode) {
        resetBtn.classList.add("dark-theme");
      }
      resetBtn.innerHTML = "↻";
      resetBtn.title = "Reset zoom and pan";
      const diagramStyle = window.getComputedStyle(diagram);
      const marginTop = parseFloat(diagramStyle.marginTop) || 0;
      const marginRight = parseFloat(diagramStyle.marginRight) || 0;
      const paddingTop = parseFloat(diagramStyle.paddingTop) || 0;
      const paddingRight = parseFloat(diagramStyle.paddingRight) || 0;
      resetBtn.style.cssText = `
                position: absolute;
                top: ${marginTop + paddingTop}px;
                right: ${marginRight + paddingRight + 10}px;
                width: 28px;
                height: 28px;
                background: ${darkMode ? "rgba(50, 50, 50, 0.95)" : "rgba(255, 255, 255, 0.95)"};
                border: 1px solid ${darkMode ? "rgba(255, 255, 255, 0.3)" : "rgba(0, 0, 0, 0.3)"};
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                line-height: 1;
                padding: 0;
                color: ${darkMode ? "#e0e0e0" : "#333"};
                z-index: 1000;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
                box-shadow: 0 2px 6px ${darkMode ? "rgba(255, 255, 255, 0.2)" : "rgba(0, 0, 0, 0.2)"};
            `;
      resetBtn.onmouseover = () => {
        resetBtn.style.opacity = "100%";
        resetBtn.style.background = darkMode
          ? "rgba(60, 60, 60, 1)"
          : "rgba(255, 255, 255, 1)";
        resetBtn.style.boxShadow = darkMode
          ? "0 3px 10px rgba(255, 255, 255, 0.2)"
          : "0 3px 10px rgba(0, 0, 0, 0.3)";
        resetBtn.style.transform = "scale(1.1)";
      };
      resetBtn.onmouseout = () => {
        resetBtn.style.opacity = "";
        resetBtn.style.background = darkMode
          ? "rgba(50, 50, 50, 0.95)"
          : "rgba(255, 255, 255, 0.95)";
        resetBtn.style.boxShadow = darkMode
          ? "0 2px 6px rgba(255, 255, 255, 0.2)"
          : "0 2px 6px rgba(0, 0, 0, 0.2)";
        resetBtn.style.transform = "";
      };
      resetBtn.onclick = () => {
        const gElement = svg.querySelector("g");
        if (gElement) {
          gElement.removeAttribute("transform");
          const zoom = svg.__zoom;
          if (zoom) {
            zoom.k = 1;
            zoom.x = 0;
            zoom.y = 0;
          }
        }
      };
      diagram.style.position = "relative";
      diagram.appendChild(resetBtn);
    });
  };
  setTimeout(addResetButtons, 100);
  const observer = new MutationObserver(() => setTimeout(addResetButtons, 100));
  observer.observe(document.body, { childList: true, subtree: true });
});
