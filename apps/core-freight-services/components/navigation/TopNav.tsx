"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";

const navLinks: Array<{ href: Route; label: string }> = [
  { href: "/", label: "Dashboard" },
  { href: "/settings", label: "Settings" }
];

export const TopNav = () => {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="flex items-center gap-2 text-sm font-medium">
      {navLinks.map((link) => {
        const isActive =
          link.href === "/" ? pathname === link.href : pathname?.startsWith(link.href);

        return (
          <Link
            key={link.href}
            aria-current={isActive ? "page" : undefined}
            className={`rounded-full px-4 py-2 transition-colors ${
              isActive ? "bg-primary text-white" : "text-primary/80 hover:bg-primary/10"
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
