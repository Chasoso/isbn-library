export const readingStatuses = ["未読", "読書中", "完了"] as const;

export type ReadingStatus = (typeof readingStatuses)[number];
