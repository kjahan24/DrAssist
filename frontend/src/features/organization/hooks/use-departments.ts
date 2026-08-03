"use client";

import { useQuery } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import { listDepartments, type DepartmentListParams } from "@/lib/mock/departments";

export const departmentKeys = createQueryKeys<DepartmentListParams>("departments");

export function useDepartments(params: DepartmentListParams = {}) {
  return useQuery({
    queryKey: departmentKeys.list(params),
    queryFn: () => listDepartments(params),
  });
}
