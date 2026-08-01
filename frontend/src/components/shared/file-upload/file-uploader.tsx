"use client";

import { useState } from "react";

import { FileDropzone } from "@/components/shared/file-upload/file-dropzone";
import { FileListItem, type UploadableFile } from "@/components/shared/file-upload/file-list-item";

interface FileUploaderProps {
  accept?: string;
  multiple?: boolean;
  maxSizeBytes?: number;
  disabled?: boolean;
  // Left to the caller: this component owns file *selection* state only,
  // never the upload request itself (attachments/documents modules will
  // each have their own upload use case) — see rule against embedding
  // business logic in UI components.
  onFilesChange?: (files: UploadableFile[]) => void;
}

export function FileUploader({
  accept,
  multiple = true,
  maxSizeBytes,
  disabled,
  onFilesChange,
}: FileUploaderProps) {
  const [files, setFiles] = useState<UploadableFile[]>([]);

  function addFiles(newFiles: File[]) {
    const items: UploadableFile[] = newFiles.map((file) => ({
      id: crypto.randomUUID(),
      file,
      progress: 0,
      status: "idle",
    }));
    const next = multiple ? [...files, ...items] : items;
    setFiles(next);
    onFilesChange?.(next);
  }

  function removeFile(id: string) {
    const next = files.filter((item) => item.id !== id);
    setFiles(next);
    onFilesChange?.(next);
  }

  return (
    <div className="space-y-3">
      <FileDropzone
        onFilesSelected={addFiles}
        accept={accept}
        multiple={multiple}
        maxSizeBytes={maxSizeBytes}
        disabled={disabled}
      />
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((item) => (
            <FileListItem key={item.id} item={item} onRemove={removeFile} />
          ))}
        </div>
      )}
    </div>
  );
}
