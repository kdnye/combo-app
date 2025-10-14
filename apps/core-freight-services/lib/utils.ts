import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge class names with Tailwind awareness.
 * Ensures deterministic order and prevents duplicate utilities.
 */
export const cn = (...inputs: ClassValue[]): string => twMerge(clsx(inputs));
