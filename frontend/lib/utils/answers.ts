import { QuestionOption, SelectedAnswerOption } from '@/types';

const VALID_OPTIONS: ('A' | 'B' | 'C' | 'D')[] = ['A', 'B', 'C', 'D'];

/**
 * Converts a UI option id or string into canonical "A" | "B" | "C" | "D" | null
 */
export function toSelectedAnswer(
  optionId: string | null | undefined,
  options?: QuestionOption[]
): SelectedAnswerOption {
  if (!optionId) return null;
  const trimmed = optionId.trim().toUpperCase();

  if (VALID_OPTIONS.includes(trimmed as any)) {
    return trimmed as 'A' | 'B' | 'C' | 'D';
  }

  // If question options list is provided, find index
  if (options && options.length > 0) {
    const idx = options.findIndex(o => o.id === optionId);
    if (idx >= 0 && idx < 4) {
      return VALID_OPTIONS[idx];
    }
  }

  // Common option id naming patterns
  if (trimmed.endsWith('-A') || trimmed.endsWith('-1') || trimmed.endsWith('_1')) return 'A';
  if (trimmed.endsWith('-B') || trimmed.endsWith('-2') || trimmed.endsWith('_2')) return 'B';
  if (trimmed.endsWith('-C') || trimmed.endsWith('-3') || trimmed.endsWith('_3')) return 'C';
  if (trimmed.endsWith('-D') || trimmed.endsWith('-4') || trimmed.endsWith('_4')) return 'D';
  if (trimmed === '1') return 'A';
  if (trimmed === '2') return 'B';
  if (trimmed === '3') return 'C';
  if (trimmed === '4') return 'D';

  return null;
}

/**
 * Resolves a backend "A" | "B" | "C" | "D" back to the corresponding option id for UI radio matching
 */
export function fromSelectedAnswer(
  selectedAnswer: SelectedAnswerOption,
  options?: QuestionOption[]
): string | undefined {
  if (!selectedAnswer) return undefined;
  const upper = selectedAnswer.toUpperCase();

  if (options && options.length > 0) {
    // Check if an option has this exact ID
    const directMatch = options.find(o => o.id.toUpperCase() === upper);
    if (directMatch) return directMatch.id;

    // Check by index A -> 0, B -> 1, C -> 2, D -> 3
    const indexMap: Record<string, number> = { A: 0, B: 1, C: 2, D: 3 };
    const idx = indexMap[upper];
    if (idx !== undefined && options[idx]) {
      return options[idx].id;
    }
  }

  return upper;
}
