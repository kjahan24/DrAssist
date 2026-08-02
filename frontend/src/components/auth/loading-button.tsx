import { Loader2 } from "lucide-react";
import type { ComponentProps } from "react";

import { Button } from "@/components/ui/button";

interface LoadingButtonProps extends ComponentProps<typeof Button> {
  loading?: boolean;
}

// Generic — not auth-specific — but introduced by this module; any future
// module's async submit button can reuse it instead of hand-rolling the
// same disabled+spinner logic.
export function LoadingButton({ loading, disabled, children, ...props }: LoadingButtonProps) {
  return (
    <Button disabled={loading || disabled} {...props}>
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
      {children}
    </Button>
  );
}
