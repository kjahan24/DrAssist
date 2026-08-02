"use client";

import { Suspense, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { LogIn } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthButton } from "@/components/auth/auth-button";
import { AuthCard } from "@/components/auth/auth-card";
import { AuthForm } from "@/components/auth/auth-form";
import { ErrorAlert } from "@/components/auth/error-alert";
import { PasswordInput } from "@/components/auth/password-input";
import { FormInput } from "@/components/shared/forms/form-input";
import { Checkbox } from "@/components/ui/checkbox";
import { FormControl, FormField, FormItem, FormLabel } from "@/components/ui/form";
import { ApiError, httpClient } from "@/lib/api-client";
import { applyServerErrors } from "@/lib/auth/apply-server-errors";
import { tokenStorage } from "@/lib/auth/token-storage";
import { useAuthStore } from "@/store/auth-store";
import type { AuthenticatedPrincipal } from "@/types";

const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
  rememberMe: z.boolean(),
});

type LoginValues = z.infer<typeof loginSchema>;
const LOGIN_FIELDS = ["email", "password"] as const;

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
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", rememberMe: false },
  });

  // The backend's Authentication module does not expose a token-issuance
  // endpoint yet — `POST /auth/login` is not implemented server-side (see
  // `app/modules/authentication/domain/exceptions.py`'s own module
  // docstring, which reserves several exceptions — DuplicateEmailError,
  // AccountLockedError, InactiveAccountError, and others — for this
  // not-yet-built flow). This form is wired to that module's documented
  // future shape so it works immediately once the backend adds it; today,
  // submitting surfaces a real (not faked) error below — a known,
  // pre-existing backend gap, not a defect in this form.
  const loginMutation = useMutation({
    mutationFn: (values: LoginValues) =>
      httpClient.post<LoginResponse>("/auth/login", {
        email: values.email,
        password: values.password,
      }),
    onSuccess: ({ data }) => {
      tokenStorage.set(data.access_token, { rememberMe: form.getValues("rememberMe") });
      setPrincipal(data.principal);
      router.push(searchParams.get("from") ?? "/dashboard");
    },
    onError: (error) => {
      const fieldsSet = applyServerErrors(error, form.setError, LOGIN_FIELDS);
      setFormError(
        fieldsSet > 0
          ? null
          : error instanceof ApiError
            ? error.message
            : "Unable to sign in. Please try again.",
      );
    },
  });

  return (
    <AuthCard
      icon={LogIn}
      title="Sign in"
      description="Sign in to your DrAssist account"
      footer={
        <p className="text-center text-sm text-muted-foreground">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="font-medium text-primary hover:underline">
            Create one
          </Link>
        </p>
      }
    >
      <AuthForm
        form={form}
        onSubmit={(values) => {
          setFormError(null);
          loginMutation.mutate(values);
        }}
      >
        <ErrorAlert message={formError} />
        <FormInput
          control={form.control}
          name="email"
          label="Email"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
        />
        <PasswordInput
          control={form.control}
          name="password"
          label="Password"
          autoComplete="current-password"
        />
        <div className="flex items-center justify-between">
          <FormField
            control={form.control}
            name="rememberMe"
            render={({ field }) => (
              <FormItem className="flex flex-row items-center gap-2 space-y-0">
                <FormControl>
                  <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
                <FormLabel className="cursor-pointer text-sm font-normal">Remember me</FormLabel>
              </FormItem>
            )}
          />
          <Link
            href="/forgot-password"
            className="text-sm font-medium text-primary hover:underline"
          >
            Forgot password?
          </Link>
        </div>
        <AuthButton loading={loginMutation.isPending}>
          {loginMutation.isPending ? "Signing in..." : "Sign in"}
        </AuthButton>
      </AuthForm>
    </AuthCard>
  );
}
