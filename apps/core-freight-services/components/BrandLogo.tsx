'use client';

import Image from 'next/image';
import { useState } from 'react';

type BrandLogoProps = {
  className?: string;
  size?: number;
};

export const BrandLogo = ({ className, size = 48 }: BrandLogoProps) => {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <span className={className} aria-label="FSI logo text fallback">
        FSI
      </span>
    );
  }

  return (
    <Image
      alt="Freight Services International logo"
      className={className}
      height={size}
      src="/brand/fsi-logo.svg"
      width={size}
      onError={() => setHasError(true)}
      priority
    />
  );
};
