import { create } from "zustand";

export interface ConfirmOptions {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "default" | "destructive";
}

interface ModalState {
  confirmOptions: ConfirmOptions | null;
  resolver: ((confirmed: boolean) => void) | null;
  confirm: (options: ConfirmOptions) => Promise<boolean>;
  resolve: (confirmed: boolean) => void;
}

// Imperative confirm-dialog orchestration: any component can `await
// confirm({...})` without rendering its own <AlertDialog>. A single
// <ConfirmDialogProvider/> (components/shared/modals) mounted once in
// providers.tsx renders whatever this store's current `confirmOptions` is.
export const useModalStore = create<ModalState>((set, get) => ({
  confirmOptions: null,
  resolver: null,
  confirm: (options) =>
    new Promise<boolean>((resolve) => {
      set({ confirmOptions: options, resolver: resolve });
    }),
  resolve: (confirmed) => {
    get().resolver?.(confirmed);
    set({ confirmOptions: null, resolver: null });
  },
}));
