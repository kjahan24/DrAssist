"use client";

import { useEffect, useState } from "react";

// Guards client-only rendering (anything that would read `window`, a
// theme, or other browser-only state before hydration) to avoid
// server/client markup mismatches.
export function useMounted(): boolean {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted;
}
