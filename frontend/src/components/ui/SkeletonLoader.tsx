import React from 'react';
import { cn } from '../../lib/utils';

export interface SkeletonLoaderProps {
  className?: string;
  variant?: 'text' | 'rectangular' | 'circular';
  width?: string | number;
  height?: string | number;
  count?: number;
}

export const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  className,
  variant = 'rectangular',
  width,
  height,
  count = 1,
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'circular':
        return 'rounded-full';
      case 'text':
        return 'h-4 rounded my-1';
      case 'rectangular':
      default:
        return 'rounded-md';
    }
  };

  const items = Array.from({ length: count });

  return (
    <>
      {items.map((_, i) => (
        <div
          key={i}
          className={cn(
            'skeleton bg-[#1e293b]/50 animate-pulse border border-[#1e3a5f]/30',
            getVariantStyles(),
            className
          )}
          style={{
            width: width !== undefined ? width : undefined,
            height: height !== undefined ? height : undefined,
          }}
        />
      ))}
    </>
  );
};
