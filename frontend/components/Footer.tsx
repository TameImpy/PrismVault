export default function Footer() {
  return (
    <footer className="w-full py-10 bg-[#05070a] border-t border-white/5">
      <div className="max-w-screen-2xl mx-auto px-8 flex flex-col md:flex-row justify-between items-center text-sm">
        <div className="flex items-center gap-2 font-headline font-bold text-white tracking-tight mb-4 md:mb-0">
          <span className="w-1.5 h-5 bg-accent-cyan rounded-full" />
          Prism Plan
        </div>
        <p className="text-slate-500">&copy; 2026 Prism Plan</p>
      </div>
    </footer>
  );
}
