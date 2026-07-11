import { cn } from "@/lib/cn";
import { Inbox } from "lucide-react";
import { Button } from "./Button";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: { label: string; onClick: () => void };
  className?: string;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center px-6 py-14 text-center",
        className
      )}
    >
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-chrome-100 text-chrome-500">
        {icon ?? <Inbox className="h-5 w-5" aria-hidden />}
      </div>
      <p className="text-sm font-semibold text-chrome-900">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-chrome-500">{description}</p>
      {action && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
