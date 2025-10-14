'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

type NavLink = {
  href: string;
  label: string;
};

type TopNavProps = {
  links: NavLink[];
};

export const TopNav = ({ links }: TopNavProps) => {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="flex items-center gap-2 text-sm font-medium">
      {links.map((link) => {
        const isActive = pathname === link.href;

        return (
          <Link
            key={link.href}
            className={`rounded-full px-4 py-2 transition-colors ${
              isActive ? 'bg-primary text-white' : 'text-primary/80 hover:bg-primary/10'
            }`}
            href={link.href}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
};
