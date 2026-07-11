import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "tertiary" | "danger";
type Size = "sm" | "md";

const VARIANT: Record<Variant, string> = {
  primary:
    "bg-accent text-accent-foreground hover:bg-accent-hover border border-transparent",
  secondary:
    "bg-white text-chrome-700 border border-chrome-200 hover:bg-chrome-50",
  tertiary:
    "bg-transparent text-chrome-600 border border-transparent hover:bg-chrome-100 hover:text-chrome-800",
  danger:
    "bg-risk-escalate text-white border border-transparent hover:bg-red-800",
};

const SIZE: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
};

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  disabled,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors",
        "disabled:pointer-events-none disabled:opacity-50",
        VARIANT[variant],
        SIZE[size],
        className
      )}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  );
}
