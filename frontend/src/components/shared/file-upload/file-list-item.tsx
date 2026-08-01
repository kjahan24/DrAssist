import { File, X } from "lucide-react";

import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { formatFileSize } from "@/lib/format";

export interface UploadableFile {
  id: string;
  file: File;
  progress: number;
  status: "idle" | "uploading" | "success" | "error";
  errorMessage?: string;
}

interface FileListItemProps {
  item: UploadableFile;
  onRemove: (id: string) => void;
}

export function FileListItem({ item, onRemove }: FileListItemProps) {
  return (
    <div className="flex items-center gap-3 rounded-md border p-3">
      <File className="size-5 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-sm font-medium">{item.file.name}</p>
          <span className="shrink-0 text-xs text-muted-foreground">
            {formatFileSize(item.file.size)}
          </span>
        </div>
        {item.status === "uploading" && <Progress value={item.progress} className="h-1.5" />}
        {item.status === "error" && (
          <p className="text-xs text-destructive">{item.errorMessage ?? "Upload failed"}</p>
        )}
      </div>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-7 shrink-0"
        onClick={() => onRemove(item.id)}
        aria-label={`Remove ${item.file.name}`}
      >
        <X className="size-4" />
      </Button>
    </div>
  );
}
