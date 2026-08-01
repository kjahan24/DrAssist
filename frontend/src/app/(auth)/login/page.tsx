"use client";

import { Suspense } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { FormInput } from "@/components/shared/forms/form-input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Form } from "@/components/ui/form";
import { ApiError, httpClient } from "@/lib/api-client";
import { tokenStorage } from "@/lib/auth/token-storage";
import { useAuthStore } from "@/store/auth-store";
import type { AuthenticatedPrincipal } from "@/types";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginValues = z.infer<typeof loginSchema>;

interface LoginResponse {
  access_token: string;
  principal: AuthenticatedPrincipal;
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setPrincipal = useAuthStore((state) => state.setPrincipal);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  // The backend's Authentication module does not expose a token-issuance
  // endpoint yet — `POST /auth/login` is not implemented server-side (see
  // `app/modules/authentication/domain/exceptions.py`'s own module
  // docstring, which reserves several exceptions for this not-yet-built
  // flow). This form is wired to that module's documented future shape so
  // it works immediately once the backend adds it; today, submitting will
  // surface a 404 via the toast below — a known, pre-existing backend gap,
  // not a defect in this form.
  const loginMutation = useMutation({
    mutationFn: (values: LoginValues) => httpClient.post<LoginResponse>("/auth/login", values),
    onSuccess: ({ data }) => {
      tokenStorage.set(data.access_token);
      setPrincipal(data.principal);
      router.push(searchParams.get("from") ?? "/dashboard");
    },
    onError: (error) => {
      toast.error(error instanceof ApiError ? error.message : "Unable to sign in");
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>Sign in to your DrAssist account</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((values) => loginMutation.mutate(values))}
            className="space-y-4"
          >
            <FormInput
              control={form.control}
              name="email"
              label="Email"
              type="email"
              placeholder="you@example.com"
            />
            <FormInput control={form.control} name="password" label="Password" type="password" />
            <Button type="submit" className="w-full" disabled={loginMutation.isPending}>
              {loginMutation.isPending ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
