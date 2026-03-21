export default function Footer() {
  return (
    <footer className="w-full pt-20 pb-10 bg-[#05070a] border-t border-white/5">
      <div className="max-w-screen-2xl mx-auto px-8 grid grid-cols-1 md:grid-cols-4 gap-12 font-body text-sm leading-relaxed">
        <div className="col-span-1">
          <div className="text-xl font-bold text-white tracking-tight mb-6 flex items-center gap-2 font-headline">
            <span className="w-1.5 h-5 bg-accent-cyan rounded-full" />
            Prism Data Vault
          </div>
          <p className="text-slate-500 mb-8">
            Leading the transition from static storage to dynamic architectural
            clarity with deep-sea security protocols.
          </p>
        </div>
        <div>
          <h4 className="text-white font-bold mb-6 font-headline">Platform</h4>
          <ul className="space-y-4 text-slate-500">
            <li className="hover:text-accent-cyan transition-colors duration-200 cursor-pointer">
              Vault Engine
            </li>
            <li className="hover:text-accent-cyan transition-colors duration-200 cursor-pointer">
              Analytics
            </li>
            <li className="hover:text-accent-cyan transition-colors duration-200 cursor-pointer">
              Security
            </li>
            <li className="hover:text-accent-cyan transition-colors duration-200 cursor-pointer">
              Integrations
            </li>
          </ul>
        </div>
        <div>
          <h4 className="text-white font-bold mb-6 font-headline">Company</h4>
          <ul className="space-y-4 text-slate-500">
            <li className="hover:text-accent-cyan transition-colors duration-200 cursor-pointer">
              About Us
            </li>
            <li className="hover:text-accent-cyan transition-colors duration-200 cursor-pointer">
              Careers
            </li>
            <li className="hover:text-accent-cyan transition-colors duration-200 cursor-pointer">
              Press
            </li>
            <li className="hover:text-accent-cyan transition-colors duration-200 cursor-pointer">
              Contact
            </li>
          </ul>
        </div>
        <div>
          <h4 className="text-white font-bold mb-6 font-headline">
            Resources
          </h4>
          <ul className="space-y-4 text-slate-500">
            <li className="hover:text-accent-cyan transition-colors duration-200 cursor-pointer">
              Security
            </li>
            <li className="hover:text-accent-cyan transition-colors duration-200 cursor-pointer">
              Status
            </li>
            <li className="hover:text-accent-cyan transition-colors duration-200 cursor-pointer">
              Privacy
            </li>
            <li className="hover:text-accent-cyan transition-colors duration-200 cursor-pointer">
              Terms
            </li>
          </ul>
        </div>
      </div>
      <div className="max-w-screen-2xl mx-auto px-8 mt-20 pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center text-slate-500">
        <p>&copy; 2024 Prism Data Vault. Deep-Sea Architectural Clarity.</p>
        <div className="flex space-x-6 mt-4 md:mt-0">
          <a href="#" className="hover:text-accent-cyan transition-colors">
            Privacy
          </a>
          <a href="#" className="hover:text-accent-cyan transition-colors">
            Terms
          </a>
          <a href="#" className="hover:text-accent-cyan transition-colors">
            Sitemap
          </a>
        </div>
      </div>
    </footer>
  );
}
