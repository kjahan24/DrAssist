import type { LucideIcon } from "lucide-react";

import { Card, CardContent, CardDescription, CardFooter, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface AuthCardProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

// Every standalone auth page (Login, Register, Forgot/Reset Password,
// Verify Email, Session Expired, Unauthorized, Access Denied, ...) is
// exactly one of these — so its title is that page's *only* heading, a
// real <h1>, not the <div> shadcn's own CardTitle renders (which would
// leave every one of these pages with zero real headings — the same
// class of WCAG bug found and fixed on the marketing pages).
export function AuthCard({
  icon: Icon,
  title,
  description,
  children,
  footer,
  className,
}: AuthCardProps) {
  return (
    <Card className={cn(className)}>
      <CardHeader className="space-y-2 text-center">
        {Icon && (
          <div className="mx-auto flex size-10 items-center justify-center rounded-full bg-primary/10">
            <Icon className="size-5 text-primary" aria-hidden="true" />
          </div>
        )}
        <h1 className="text-xl font-semibold leading-none tracking-tight">{title}</h1>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
      {footer && <CardFooter className="flex flex-col gap-4">{footer}</CardFooter>}
    </Card>
  );
}
