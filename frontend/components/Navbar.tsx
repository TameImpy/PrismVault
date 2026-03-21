import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="fixed top-0 w-full z-50 bg-[#0a0c10]/80 backdrop-blur-[20px] border-b border-white/5 shadow-2xl">
      <div className="flex justify-between items-center px-8 py-5 max-w-screen-2xl mx-auto">
        <Link
          href="/"
          className="text-2xl font-bold tracking-tighter text-white font-headline flex items-center gap-2"
        >
          <span className="w-2 h-6 bg-accent-cyan rounded-full" />
          Prism Data Vault
        </Link>

        <div className="hidden md:flex items-center space-x-10 font-headline font-semibold tracking-tight">
          <Link
            href="/"
            className="text-slate-400 hover:text-white transition-all duration-300"
          >
            Products
          </Link>
          <Link
            href="/#pricing"
            className="text-slate-400 hover:text-white transition-all duration-300"
          >
            Pricing
          </Link>
          <Link
            href="/app"
            className="text-accent-cyan border-b-2 border-accent-cyan pb-1 transition-all duration-300"
          >
            Insights Tool
          </Link>
          <Link
            href="/#resources"
            className="text-slate-400 hover:text-white transition-all duration-300"
          >
            Resources
          </Link>
        </div>

        <div className="flex items-center space-x-6">
          <button className="text-slate-400 font-semibold hover:text-white active:scale-95 transition-all">
            Login
          </button>
          <Link
            href="/app"
            className="refractive-gradient px-6 py-2.5 rounded-xl font-bold text-white shadow-lg active:scale-95 transition-transform inline-block"
          >
            Launch App
          </Link>
        </div>
      </div>
    </nav>
  );
}
