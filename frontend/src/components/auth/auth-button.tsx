import type { ComponentProps } from "react";

import { LoadingButton } from "@/components/auth/loading-button";
import { cn } from "@/lib/utils";

type AuthButtonProps = ComponentProps<typeof LoadingButton>;

// The full-width primary submit button every auth form ends with.
export function AuthButton({ className, size = "lg", type = "submit", ...props }: AuthButtonProps) {
  return <LoadingButton type={type} size={size} className={cn("w-full", className)} {...props} />;
}
