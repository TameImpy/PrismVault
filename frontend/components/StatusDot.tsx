export default function StatusDot({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center space-x-2 px-3 py-1 bg-surface-container-high rounded-full border border-white/5">
      <span className="w-2 h-2 rounded-full bg-accent-cyan animate-pulse" />
      {label && (
        <span className="text-[10px] font-bold tracking-widest text-accent-cyan uppercase">
          {label}
        </span>
      )}
    </span>
  );
}
