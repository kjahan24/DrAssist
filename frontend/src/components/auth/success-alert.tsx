import { CheckCircle2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface SuccessAlertProps {
  title?: string;
  message?: string | null;
}

export function SuccessAlert({ title = "Success", message }: SuccessAlertProps) {
  if (!message) return null;

  return (
    <Alert variant="success">
      <CheckCircle2 className="size-4" aria-hidden="true" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
