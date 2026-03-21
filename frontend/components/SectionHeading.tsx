interface SectionHeadingProps {
  children: React.ReactNode;
  subtitle?: string;
}

export default function SectionHeading({
  children,
  subtitle,
}: SectionHeadingProps) {
  return (
    <div className="mb-20">
      <h2 className="font-headline text-4xl md:text-5xl font-bold tracking-tight mb-4">
        {children}
      </h2>
      <div className="w-20 h-1 refractive-gradient rounded-full" />
      {subtitle && (
        <p className="text-slate-400 mt-6 max-w-xl">{subtitle}</p>
      )}
    </div>
  );
}
