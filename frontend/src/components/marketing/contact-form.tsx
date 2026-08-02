"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Mail } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormInput } from "@/components/shared/forms/form-input";
import { FormTextarea } from "@/components/shared/forms/form-textarea";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Form } from "@/components/ui/form";
import { siteConfig } from "@/config/site";

const contactSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Enter a valid email address"),
  organization: z.string().optional(),
  message: z.string().min(10, "Message must be at least 10 characters"),
});

type ContactValues = z.infer<typeof contactSchema>;

// No contact-form backend endpoint exists yet, so submitting composes a
// mailto: link from the visitor's own input rather than faking a
// successful API call — genuinely functional, not a stub, and consistent
// with this module's "no fake business logic" rule.
export function ContactForm() {
  const form = useForm<ContactValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: { name: "", email: "", organization: "", message: "" },
  });

  function onSubmit(values: ContactValues) {
    const subject = encodeURIComponent(`DrAssist inquiry from ${values.name}`);
    const body = encodeURIComponent(
      `${values.message}\n\n— ${values.name} (${values.email})${
        values.organization ? `\n${values.organization}` : ""
      }`,
    );
    window.location.href = `mailto:${siteConfig.contactEmail}?subject=${subject}&body=${body}`;
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormInput control={form.control} name="name" label="Name" placeholder="Jane Doe" />
            <FormInput
              control={form.control}
              name="email"
              label="Email"
              type="email"
              placeholder="you@example.com"
            />
            <FormInput
              control={form.control}
              name="organization"
              label="Organization (optional)"
              placeholder="Acme Clinic"
            />
            <FormTextarea
              control={form.control}
              name="message"
              label="Message"
              placeholder="Tell us about your team and what you're looking for."
            />
            <Button type="submit" className="w-full">
              <Mail className="size-4" />
              Send Message
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
