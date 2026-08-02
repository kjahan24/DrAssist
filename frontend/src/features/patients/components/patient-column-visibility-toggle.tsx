"use client";

import type { VisibilityState } from "@tanstack/react-table";
import { SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ToggleableColumn {
  id: string;
  label: string;
}

interface PatientColumnVisibilityToggleProps {
  columns: ToggleableColumn[];
  columnVisibility: VisibilityState;
  onColumnVisibilityChange: (next: VisibilityState) => void;
}

// Plain, parent-owned `VisibilityState` rather than reading off a live
// TanStack `Table` instance — `DataTable` (`components/shared/data-table`)
// doesn't expose the instance it builds internally, and giving it a
// second, purpose-built instance just to list column ids would be more
// coupling than this needs for seven fixed, known columns.
export function PatientColumnVisibilityToggle({
  columns,
  columnVisibility,
  onColumnVisibilityChange,
}: PatientColumnVisibilityToggleProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <SlidersHorizontal className="size-4" />
          Columns
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {columns.map((column) => {
          const isVisible = columnVisibility[column.id] !== false;
          return (
            <DropdownMenuCheckboxItem
              key={column.id}
              checked={isVisible}
              onCheckedChange={(value) =>
                onColumnVisibilityChange({ ...columnVisibility, [column.id]: Boolean(value) })
              }
              onSelect={(event) => event.preventDefault()}
            >
              {column.label}
            </DropdownMenuCheckboxItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
