"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  type ClinicalNoteFormInput,
  type ClinicalNoteListParams,
  createClinicalNote,
  getClinicalNote,
  listClinicalNotes,
  updateClinicalNote,
} from "@/lib/mock/clinical-notes";

// Same `createQueryKeys` factory every feature module uses — swapping
// the mock functions below for real `httpClient` calls later touches
// only this file.
export const clinicalNoteKeys = createQueryKeys<ClinicalNoteListParams>("clinical-notes");

export function useClinicalNotes(params: ClinicalNoteListParams) {
  return useQuery({
    queryKey: clinicalNoteKeys.list(params),
    queryFn: () => listClinicalNotes(params),
  });
}

export function useClinicalNote(clinicalNoteId: string) {
  return useQuery({
    queryKey: clinicalNoteKeys.detail(clinicalNoteId),
    queryFn: () => getClinicalNote(clinicalNoteId),
    enabled: Boolean(clinicalNoteId),
  });
}

export function useCreateClinicalNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: ClinicalNoteFormInput) => createClinicalNote(input),
    onSuccess: (note) => {
      queryClient.invalidateQueries({ queryKey: clinicalNoteKeys.lists() });
      queryClient.setQueryData(clinicalNoteKeys.detail(note.clinical_note_id), note);
    },
  });
}

export function useUpdateClinicalNote(clinicalNoteId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ input, action }: { input: ClinicalNoteFormInput; action: "draft" | "sign" }) =>
      updateClinicalNote(clinicalNoteId, input, action),
    onSuccess: (note) => {
      queryClient.invalidateQueries({ queryKey: clinicalNoteKeys.lists() });
      queryClient.setQueryData(clinicalNoteKeys.detail(clinicalNoteId), note);
    },
  });
}
