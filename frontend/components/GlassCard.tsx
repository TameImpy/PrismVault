import { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
}

export default function GlassCard({ children, className = "" }: GlassCardProps) {
  return (
    <div
      className={`glass-card rounded-2xl p-6 border border-white/10 shadow-2xl ${className}`}
    >
      {children}
    </div>
  );
}
