"use client";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useModalStore } from "@/store/modal-store";

// Single, app-wide mount point for `useConfirm()` (`hooks/use-confirm.ts`),
// rendered once from `providers.tsx`. Renders nothing while no
// confirmation is pending.
export function ConfirmDialogProvider() {
  const options = useModalStore((state) => state.confirmOptions);
  const resolve = useModalStore((state) => state.resolve);

  return (
    <AlertDialog open={options !== null} onOpenChange={(open) => !open && resolve(false)}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{options?.title}</AlertDialogTitle>
          {options?.description && (
            <AlertDialogDescription>{options.description}</AlertDialogDescription>
          )}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={() => resolve(false)}>
            {options?.cancelLabel ?? "Cancel"}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={() => resolve(true)}
            className={cn(
              options?.variant === "destructive" && buttonVariants({ variant: "destructive" }),
            )}
          >
            {options?.confirmLabel ?? "Confirm"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
