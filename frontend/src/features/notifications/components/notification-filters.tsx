"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  NOTIFICATION_CATEGORY_OPTIONS,
  NOTIFICATION_PRIORITY_OPTIONS,
  type NotificationCategory,
  type NotificationPriority,
} from "@/lib/mock/notifications";

interface NotificationFiltersProps {
  category: NotificationCategory | "all";
  onCategoryChange: (category: NotificationCategory | "all") => void;
  priority: NotificationPriority | "all";
  onPriorityChange: (priority: NotificationPriority | "all") => void;
  readStatus: "all" | "unread" | "read";
  onReadStatusChange: (readStatus: "all" | "unread" | "read") => void;
}

export function NotificationFilters({
  category,
  onCategoryChange,
  priority,
  onPriorityChange,
  readStatus,
  onReadStatusChange,
}: NotificationFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={readStatus}
        onValueChange={(value) => onReadStatusChange(value as "all" | "unread" | "read")}
      >
        <SelectTrigger className="w-32" aria-label="Filter by read status">
          <SelectValue placeholder="Read Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All</SelectItem>
          <SelectItem value="unread">Unread</SelectItem>
          <SelectItem value="read">Read</SelectItem>
        </SelectContent>
      </Select>

      <Select
        value={category}
        onValueChange={(value) => onCategoryChange(value as NotificationCategory | "all")}
      >
        <SelectTrigger className="w-44" aria-label="Filter by category">
          <SelectValue placeholder="Category" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All categories</SelectItem>
          {NOTIFICATION_CATEGORY_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={priority}
        onValueChange={(value) => onPriorityChange(value as NotificationPriority | "all")}
      >
        <SelectTrigger className="w-36" aria-label="Filter by priority">
          <SelectValue placeholder="Priority" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All priorities</SelectItem>
          {NOTIFICATION_PRIORITY_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
