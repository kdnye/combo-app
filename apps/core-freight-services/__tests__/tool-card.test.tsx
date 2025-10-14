import React, { forwardRef } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import type { LucideIcon, LucideProps } from 'lucide-react';
import { ToolCard } from '@/components/ToolCard';

const { usePreferencesMock } = vi.hoisted(() => ({
  usePreferencesMock: vi.fn()
}));

vi.mock('@/components/preferences/preferences-provider', () => ({
  usePreferences: usePreferencesMock
}));

const MockIcon = forwardRef<SVGSVGElement, LucideProps>((props, ref) => (
  <svg data-testid="mock-icon" ref={ref} {...props} />
)) as unknown as LucideIcon;

describe('ToolCard', () => {
  beforeEach(() => {
    usePreferencesMock.mockReturnValue({
      openLinksInNewTab: false,
      setOpenLinksInNewTab: vi.fn()
    });
  });

  it('returns null when hidden', () => {
    const { container } = render(
      <ToolCard
        description="Test"
        hidden
        href="https://example.com"
        icon={MockIcon}
        title="Hidden Tool"
      />,
    );

    expect(container.firstChild).toBeNull();
  });

  it('respects open in new tab preference', () => {
    usePreferencesMock.mockReturnValue({
      openLinksInNewTab: true,
      setOpenLinksInNewTab: vi.fn()
    });

    render(
      <ToolCard
        description="Test"
        href="https://example.com"
        icon={MockIcon}
        title="Visible Tool"
      />,
    );

    const button = screen.getByRole('link', { name: /open the visible tool/i });
    expect(button).toHaveAttribute('target', '_blank');
    expect(button).toHaveAttribute('rel', 'noreferrer');
  });
});
