"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  type SOAPNoteFormInput,
  type SOAPNoteListParams,
  type SOAPNoteStatus,
  createSoapNote,
  getSoapNote,
  listSoapNotes,
  updateSoapNote,
} from "@/lib/mock/soap-notes";

// Same `createQueryKeys` factory every feature module uses — swapping
// the mock functions below for real `httpClient` calls later touches
// only this file.
export const soapNoteKeys = createQueryKeys<SOAPNoteListParams>("soap-notes");

export function useSoapNotes(params: SOAPNoteListParams) {
  return useQuery({
    queryKey: soapNoteKeys.list(params),
    queryFn: () => listSoapNotes(params),
  });
}

export function useSoapNote(soapNoteId: string) {
  return useQuery({
    queryKey: soapNoteKeys.detail(soapNoteId),
    queryFn: () => getSoapNote(soapNoteId),
    enabled: Boolean(soapNoteId),
  });
}

export function useCreateSoapNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ input, status }: { input: SOAPNoteFormInput; status: SOAPNoteStatus }) =>
      createSoapNote(input, status),
    onSuccess: (note) => {
      queryClient.invalidateQueries({ queryKey: soapNoteKeys.lists() });
      queryClient.setQueryData(soapNoteKeys.detail(note.soap_note_id), note);
    },
  });
}

export function useUpdateSoapNote(soapNoteId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ input, status }: { input: SOAPNoteFormInput; status: SOAPNoteStatus }) =>
      updateSoapNote(soapNoteId, input, status),
    onSuccess: (note) => {
      queryClient.invalidateQueries({ queryKey: soapNoteKeys.lists() });
      queryClient.setQueryData(soapNoteKeys.detail(soapNoteId), note);
    },
  });
}
