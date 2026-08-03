"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  type DocumentListParams,
  type DocumentUpdateInput,
  type DocumentUploadInput,
  createDocument,
  getDocument,
  listDocuments,
  updateDocument,
} from "@/lib/mock/documents";

// Same `createQueryKeys` factory every feature module uses — swapping
// the mock functions below for real `httpClient` calls later touches
// only this file.
export const documentKeys = createQueryKeys<DocumentListParams>("documents");

export function useDocuments(params: DocumentListParams) {
  return useQuery({
    queryKey: documentKeys.list(params),
    queryFn: () => listDocuments(params),
  });
}

export function useDocument(documentId: string) {
  return useQuery({
    queryKey: documentKeys.detail(documentId),
    queryFn: () => getDocument(documentId),
    enabled: Boolean(documentId),
  });
}

export function useCreateDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: DocumentUploadInput) => createDocument(input),
    onSuccess: (document) => {
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() });
      queryClient.setQueryData(documentKeys.detail(document.document_id), document);
    },
  });
}

export function useUpdateDocument(documentId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: DocumentUpdateInput) => updateDocument(documentId, input),
    onSuccess: (document) => {
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() });
      queryClient.setQueryData(documentKeys.detail(documentId), document);
    },
  });
}
