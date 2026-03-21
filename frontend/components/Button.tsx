import { ButtonHTMLAttributes, ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
  children: ReactNode;
}

export default function Button({
  variant = "primary",
  children,
  className = "",
  ...props
}: ButtonProps) {
  const base =
    "px-10 py-5 rounded-xl font-bold transition-all active:scale-95";
  const variants = {
    primary: "refractive-gradient text-white shadow-xl",
    secondary:
      "bg-surface-container-highest text-on-surface hover:bg-surface-bright border border-white/5",
  };

  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}
