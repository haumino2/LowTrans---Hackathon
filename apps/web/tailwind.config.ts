import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        chrome: {
          50: "var(--chrome-50)",
          100: "var(--chrome-100)",
          200: "var(--chrome-200)",
          300: "var(--chrome-300)",
          400: "var(--chrome-400)",
          500: "var(--chrome-500)",
          600: "var(--chrome-600)",
          700: "var(--chrome-700)",
          800: "var(--chrome-800)",
          900: "var(--chrome-900)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          hover: "var(--accent-hover)",
          muted: "var(--accent-muted)",
          foreground: "var(--accent-foreground)",
        },
        risk: {
          clear: "var(--risk-clear)",
          "clear-bg": "var(--risk-clear-bg)",
          review: "var(--risk-review)",
          "review-bg": "var(--risk-review-bg)",
          escalate: "var(--risk-escalate)",
          "escalate-bg": "var(--risk-escalate-bg)",
        },
      },
      borderRadius: {
        md: "0.375rem",
        lg: "0.5rem",
      },
      boxShadow: {
        sm: "0 1px 2px 0 rgb(15 23 42 / 0.05)",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
