
'use client';

import type { LucideIcon } from 'lucide-react';
import Link from 'next/link';
import { memo } from 'react';
import { usePreferences } from '@/components/preferences/preferences-provider';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export type ToolCardProps = {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
  beta?: boolean;
  hidden?: boolean;
  className?: string;
};

/**
 * Display a launcher card for a tool with consistent layout and a CTA button.
 */
const ToolCardComponent = ({
  title,
  description,
  href,
  icon: Icon,
  beta = false,
  hidden = false,
  className
}: ToolCardProps) => {
  const { openLinksInNewTab } = usePreferences();

  if (hidden) {
    return null;
  }

  const target = openLinksInNewTab ? '_blank' : undefined;
  const rel = openLinksInNewTab ? 'noreferrer' : undefined;
  const id = `${title.replace(/\s+/g, '-').toLowerCase()}-title`;

  return (
    <article className={cn('card', className)} aria-labelledby={id}>
      <header className="card-header">
        <span className="card-icon" aria-hidden="true">
          <Icon className="h-6 w-6" />
        </span>
        <div>
          <h2 className="text-lg font-semibold" id={id}>
            {title}
          </h2>
          {beta ? <span className="badge">Beta</span> : null}
        </div>
      </header>
      <p className="text-sm text-muted">{description}</p>
      <footer className="card-footer">
        <Button asChild aria-label={`Open the ${title}`}>
          <Link href={href} rel={rel} target={target}>
            Launch
          </Link>
        </Button>
      </footer>
    </article>
  );
};

export const ToolCard = memo(ToolCardComponent);
