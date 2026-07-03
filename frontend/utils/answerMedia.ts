export async function fetchAnswerMediaUrl(
  apiFetch: ReturnType<typeof useApi>["apiFetch"],
  questionId: number,
): Promise<string> {
  const blob = await apiFetch<Blob>(`/questions/${questionId}/answer/media`, {
    responseType: "blob",
  })
  return URL.createObjectURL(blob)
}
