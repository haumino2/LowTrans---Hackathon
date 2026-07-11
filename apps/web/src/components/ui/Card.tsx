import { cn } from "@/lib/cn";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
}

export function Card({ children, className, padding = true }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-chrome-200 bg-white shadow-sm",
        padding && "p-4",
        className
      )}
    >
      {children}
    </div>
  );
}
