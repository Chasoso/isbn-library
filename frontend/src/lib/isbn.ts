export const normalizeIsbn = (rawValue: string): string | null => {
  const digits = rawValue.replace(/[^0-9X]/gi, "").toUpperCase();

  if (digits.length === 13 && (digits.startsWith("978") || digits.startsWith("979"))) {
    return digits;
  }

  if (digits.length === 10) {
    return digits;
  }

  return null;
};
