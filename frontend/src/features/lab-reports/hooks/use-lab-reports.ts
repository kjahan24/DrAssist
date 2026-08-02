"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  type LabReportFormInput,
  type LabReportListParams,
  createLabReport,
  getLabReport,
  listLabReports,
  updateLabReport,
} from "@/lib/mock/lab-reports";

// Same `createQueryKeys` factory every feature module uses — swapping
// the mock functions below for real `httpClient` calls later touches
// only this file.
export const labReportKeys = createQueryKeys<LabReportListParams>("lab-reports");

export function useLabReports(params: LabReportListParams) {
  return useQuery({
    queryKey: labReportKeys.list(params),
    queryFn: () => listLabReports(params),
  });
}

export function useLabReport(labReportId: string) {
  return useQuery({
    queryKey: labReportKeys.detail(labReportId),
    queryFn: () => getLabReport(labReportId),
    enabled: Boolean(labReportId),
  });
}

export function useCreateLabReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ input, status }: { input: LabReportFormInput; status: "draft" | "final" }) =>
      createLabReport(input, status),
    onSuccess: (report) => {
      queryClient.invalidateQueries({ queryKey: labReportKeys.lists() });
      queryClient.setQueryData(labReportKeys.detail(report.lab_report_id), report);
    },
  });
}

export function useUpdateLabReport(labReportId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ input, status }: { input: LabReportFormInput; status: "draft" | "final" }) =>
      updateLabReport(labReportId, input, status),
    onSuccess: (report) => {
      queryClient.invalidateQueries({ queryKey: labReportKeys.lists() });
      queryClient.setQueryData(labReportKeys.detail(labReportId), report);
    },
  });
}
