import { cn } from "@/lib/cn";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-chrome-200/80",
        className
      )}
      aria-hidden
    />
  );
}

export function TableSkeleton({ rows = 6, cols = 8 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-0" role="status" aria-label="Loading">
      <div className="flex gap-4 border-b border-chrome-200 bg-chrome-50 px-4 py-3">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 border-b border-chrome-100 px-4 py-2.5">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-3.5 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function StatGridSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-5" role="status" aria-label="Loading stats">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-lg border border-chrome-200 bg-white p-4 shadow-sm">
          <Skeleton className="mb-2 h-7 w-16" />
          <Skeleton className="h-3 w-24" />
        </div>
      ))}
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-4 p-6" role="status" aria-label="Loading">
      <Skeleton className="h-7 w-48" />
      <Skeleton className="h-4 w-72" />
      <StatGridSkeleton />
      <div className="rounded-lg border border-chrome-200 bg-white shadow-sm">
        <TableSkeleton />
      </div>
    </div>
  );
}
