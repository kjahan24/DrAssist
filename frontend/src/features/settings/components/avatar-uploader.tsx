"use client";

import { Camera } from "lucide-react";
import { useRef, useState, type ChangeEvent } from "react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";

interface AvatarUploaderProps {
  name: string;
  avatarUrl: string | null;
  onChange: (avatarUrl: string) => void;
  disabled?: boolean;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

// No real file storage exists in this mock (same "(UI)" reasoning as
// every other upload surface in this app, e.g. `DocumentUploader`) — a
// selected file becomes a local, browser-generated preview URL
// (`URL.createObjectURL`), never actually uploaded anywhere.
export function AvatarUploader({ name, avatarUrl, onChange, disabled }: AvatarUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(avatarUrl);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    onChange(url);
  }

  return (
    <div className="flex items-center gap-4">
      <Avatar className="size-20">
        {preview && <AvatarImage src={preview} alt="" />}
        <AvatarFallback className="text-lg">{getInitials(name)}</AvatarFallback>
      </Avatar>
      <div className="space-y-1.5">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          <Camera className="size-4" />
          Change Photo
        </Button>
        <p className="text-xs text-muted-foreground">
          JPG or PNG. This is a UI preview only — nothing is uploaded.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg"
          className="hidden"
          onChange={handleFileChange}
          aria-label="Upload profile photo"
        />
      </div>
    </div>
  );
}
