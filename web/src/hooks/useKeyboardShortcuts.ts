import { useEffect } from "react";

const INPUT_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

function isInputFocused(): boolean {
  const el = document.activeElement;
  if (!el) return false;
  if (INPUT_TAGS.has(el.tagName)) return true;
  if ((el as HTMLElement).isContentEditable) return true;
  return false;
}

export function useKeyboardShortcuts() {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Ctrl+K or Cmd+K: open global search
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("open-search"));
        return;
      }

      // N: open new task (only when not typing in an input)
      if (e.key === "n" && !e.ctrlKey && !e.metaKey && !e.altKey && !isInputFocused()) {
        window.dispatchEvent(new CustomEvent("open-new-task"));
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);
}
