"use client";

import { useModalStore } from "@/store/modal-store";

// await confirm({ title: "Delete patient?", variant: "destructive" })
export function useConfirm() {
  return useModalStore((state) => state.confirm);
}
