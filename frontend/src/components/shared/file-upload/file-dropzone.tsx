"use client";

import { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";

import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  maxSizeBytes?: number;
  disabled?: boolean;
  className?: string;
}

// Pure drag-and-drop + click-to-browse surface — deliberately has no
// knowledge of *what* happens to the files it selects (no upload call, no
// business rule about which document types are valid). A feature module
// wires `onFilesSelected` to its own upload use case and owns its own
// progress-list UI on top (see `features/documents/components
// /document-uploader.tsx`, which pairs this with `FileListItem` directly).
export function FileDropzone({
  onFilesSelected,
  accept,
  multiple = true,
  maxSizeBytes,
  disabled,
  className,
}: FileDropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFiles(fileList: FileList | null) {
    if (!fileList) return;
    const files = Array.from(fileList).filter(
      (file) => maxSizeBytes === undefined || file.size <= maxSizeBytes,
    );
    if (files.length > 0) {
      onFilesSelected(files);
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(event) => event.key === "Enter" && inputRef.current?.click()}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setIsDragActive(true);
      }}
      onDragLeave={() => setIsDragActive(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragActive(false);
        if (!disabled) handleFiles(event.dataTransfer.files);
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-8 text-center transition-colors",
        isDragActive && "border-primary bg-accent",
        disabled && "pointer-events-none opacity-50",
        className,
      )}
    >
      <UploadCloud className="size-8 text-muted-foreground" />
      <p className="text-sm font-medium">Drag and drop files, or click to browse</p>
      {accept && <p className="text-xs text-muted-foreground">Accepted: {accept}</p>}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        className="hidden"
        onChange={(event) => handleFiles(event.target.files)}
      />
    </div>
  );
}
