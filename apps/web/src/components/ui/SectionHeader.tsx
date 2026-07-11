import { cn } from "@/lib/cn";

interface SectionHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function SectionHeader({
  title,
  description,
  actions,
  className,
}: SectionHeaderProps) {
  return (
    <div className={cn("mb-6 flex items-start justify-between gap-4", className)}>
      <div>
        <h2 className="text-xl font-semibold text-chrome-900">{title}</h2>
        {description && (
          <p className="mt-0.5 text-sm text-chrome-500">{description}</p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
