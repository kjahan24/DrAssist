import { create } from "zustand";

// Sidebar open/collapsed state is already owned by shadcn's own
// `SidebarProvider` (cookie-persisted internally) — it does not belong
// here. This store is for global UI state that genuinely has no other
// owner, such as the command palette, which is toggled both from a header
// button and a global keyboard shortcut and needs to be read from both.
interface UiState {
  commandMenuOpen: boolean;
  setCommandMenuOpen: (open: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  commandMenuOpen: false,
  setCommandMenuOpen: (open) => set({ commandMenuOpen: open }),
}));
