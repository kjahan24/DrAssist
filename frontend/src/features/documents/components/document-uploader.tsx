"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { FileDropzone } from "@/components/shared/file-upload/file-dropzone";
import { FileListItem, type UploadableFile } from "@/components/shared/file-upload/file-list-item";
import { FormInput } from "@/components/shared/forms/form-input";
import { FormSelect } from "@/components/shared/forms/form-select";
import { FormTextarea } from "@/components/shared/forms/form-textarea";
import { Form } from "@/components/ui/form";
import { PatientCombobox } from "@/features/appointments/components/patient-combobox";
import { DocumentFormSection } from "@/features/documents/components/document-form-section";
import { useCreateDocument } from "@/features/documents/hooks/use-documents";
import {
  DOCUMENT_CATEGORY_OPTIONS,
  type DocumentCategory,
  type DocumentUpdateInput,
  type MedicalDocumentDetail,
} from "@/lib/mock/documents";

function stripExtension(filename: string): string {
  const index = filename.lastIndexOf(".");
  return index > 0 ? filename.slice(0, index) : filename;
}

function extensionOf(filename: string): string {
  const index = filename.lastIndexOf(".");
  return index > 0 ? filename.slice(index + 1) : "";
}

// --- Upload mode -----------------------------------------------------
// The task's Upload Document bullets don't list a Title field — with
// multiple files selectable at once, one typed title couldn't apply to
// all of them anyway. Each file becomes its own document (matching the
// real backend's one-row-per-upload model), titled from its own
// filename automatically.

const uploadMetadataSchema = z.object({
  patient_id: z.string().min(1, "Select a patient"),
  category: z.string().min(1, "Select a category"),
  tags: z.string(),
  description: z.string(),
});

type UploadMetadataInput = z.infer<typeof uploadMetadataSchema>;

const EMPTY_UPLOAD_METADATA: UploadMetadataInput = {
  patient_id: "",
  category: "",
  tags: "",
  description: "",
};

function DocumentUploadForm() {
  const router = useRouter();
  const createDocument = useCreateDocument();
  const [files, setFiles] = useState<UploadableFile[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<UploadMetadataInput>({
    resolver: zodResolver(uploadMetadataSchema),
    defaultValues: EMPTY_UPLOAD_METADATA,
  });

  function addFiles(newFiles: File[]) {
    setFiles((current) => [
      ...current,
      ...newFiles.map((file) => ({
        id: crypto.randomUUID(),
        file,
        progress: 0,
        status: "idle" as const,
      })),
    ]);
  }

  function removeFile(id: string) {
    setFiles((current) => current.filter((item) => item.id !== id));
  }

  function updateFile(id: string, patch: Partial<UploadableFile>) {
    setFiles((current) => current.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  // Simulates a progress bar — no real network transfer happens for any
  // file in this mock — before writing each file's metadata via
  // `createDocument()`.
  async function simulateUpload(item: UploadableFile, metadata: UploadMetadataInput) {
    updateFile(item.id, { status: "uploading", progress: 0 });
    for (const progress of [25, 55, 80, 100]) {
      await new Promise((resolve) => setTimeout(resolve, 150));
      updateFile(item.id, { progress });
    }

    await createDocument.mutateAsync({
      patient_id: metadata.patient_id,
      category: metadata.category as DocumentCategory,
      title: stripExtension(item.file.name),
      original_filename: item.file.name,
      mime_type: item.file.type || "application/octet-stream",
      extension: extensionOf(item.file.name) || "bin",
      file_size_bytes: item.file.size,
      description: metadata.description,
      tags: metadata.tags,
    });

    updateFile(item.id, { status: "success" });
  }

  async function handleSubmit(metadata: UploadMetadataInput) {
    if (files.length === 0) {
      toast.error("Select at least one file to upload.");
      return;
    }

    setIsSubmitting(true);
    try {
      for (const item of files) {
        await simulateUpload(item, metadata);
      }
      toast.success(`${files.length} document${files.length === 1 ? "" : "s"} uploaded.`);
      router.push("/dashboard/documents");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6" noValidate>
        <DocumentFormSection title="Document Details">
          <PatientCombobox control={form.control} name="patient_id" />
          <FormSelect
            control={form.control}
            name="category"
            label="Category"
            options={DOCUMENT_CATEGORY_OPTIONS}
          />
          <div className="sm:col-span-2">
            <FormInput
              control={form.control}
              name="tags"
              label="Tags"
              placeholder="e.g. bloodwork, annual-checkup"
              description="Comma-separated."
            />
          </div>
          <div className="sm:col-span-2">
            <FormTextarea control={form.control} name="description" label="Description" rows={3} />
          </div>
        </DocumentFormSection>

        <DocumentFormSection title="Files">
          <div className="space-y-3 sm:col-span-2">
            <FileDropzone onFilesSelected={addFiles} multiple disabled={isSubmitting} />
            {files.length > 0 && (
              <div className="space-y-2">
                {files.map((item) => (
                  <FileListItem key={item.id} item={item} onRemove={removeFile} />
                ))}
              </div>
            )}
          </div>
        </DocumentFormSection>

        <div className="flex justify-end gap-3">
          <LoadingButton type="submit" loading={isSubmitting}>
            Upload{" "}
            {files.length > 0
              ? `${files.length} Document${files.length === 1 ? "" : "s"}`
              : "Documents"}
          </LoadingButton>
        </div>
      </form>
    </Form>
  );
}

// --- Edit mode -------------------------------------------------------
// The uploaded file itself is never replaceable here — only metadata
// (title/category/tags/description) — matching `updateDocument()`'s own
// `DocumentUpdateInput` shape in `lib/mock/documents.ts`.

const editSchema = z.object({
  title: z.string().min(1, "Title is required"),
  category: z.enum([
    "prescription",
    "lab_report",
    "radiology",
    "medical_image",
    "clinical_note",
    "referral_letter",
    "discharge_summary",
    "insurance",
    "consent_form",
    "vaccination",
    "other",
  ]),
  description: z.string(),
  tags: z.string(),
}) satisfies z.ZodType<DocumentUpdateInput>;

interface DocumentEditFormProps {
  document: MedicalDocumentDetail;
  defaultValues: DocumentUpdateInput;
  onSubmit: (values: DocumentUpdateInput) => void;
  isSubmitting?: boolean;
}

function DocumentEditForm({
  document,
  defaultValues,
  onSubmit,
  isSubmitting,
}: DocumentEditFormProps) {
  const form = useForm<DocumentUpdateInput>({
    resolver: zodResolver(editSchema),
    defaultValues,
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6" noValidate>
        <DocumentFormSection title="Document Details">
          <div className="sm:col-span-2">
            <FormInput control={form.control} name="title" label="Document Name" />
          </div>
          <FormSelect
            control={form.control}
            name="category"
            label="Category"
            options={DOCUMENT_CATEGORY_OPTIONS}
          />
          <div className="sm:col-span-2">
            <FormInput
              control={form.control}
              name="tags"
              label="Tags"
              placeholder="e.g. bloodwork, annual-checkup"
              description="Comma-separated."
            />
          </div>
          <div className="sm:col-span-2">
            <FormTextarea control={form.control} name="description" label="Description" rows={3} />
          </div>
        </DocumentFormSection>

        <div className="rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
          <p className="font-medium text-foreground">{document.original_filename}</p>
          <p>
            The uploaded file itself can&apos;t be replaced here — upload a new document instead.
          </p>
        </div>

        <div className="flex justify-end gap-3">
          <LoadingButton type="submit" loading={isSubmitting}>
            Save Changes
          </LoadingButton>
        </div>
      </form>
    </Form>
  );
}

// --- Public component --------------------------------------------------

type DocumentUploaderProps =
  | { mode: "upload" }
  | {
      mode: "edit";
      document: MedicalDocumentDetail;
      defaultValues: DocumentUpdateInput;
      onSubmit: (values: DocumentUpdateInput) => void;
      isSubmitting?: boolean;
    };

// The single reusable form component named by this module's task spec
// (no separate `DocumentForm`) — per "Edit Document: Reuse the same
// form." Upload mode owns its own multi-file create flow end-to-end
// (drag & drop, per-file simulated progress, one `createDocument()`
// call per file, then redirect); Edit mode is a thin controlled form
// for one existing document's metadata, delegating submission to the
// caller like every other feature module's form component.
export function DocumentUploader(props: DocumentUploaderProps) {
  if (props.mode === "edit") {
    return (
      <DocumentEditForm
        document={props.document}
        defaultValues={props.defaultValues}
        onSubmit={props.onSubmit}
        isSubmitting={props.isSubmitting}
      />
    );
  }

  return <DocumentUploadForm />;
}
