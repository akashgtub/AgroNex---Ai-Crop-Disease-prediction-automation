import { Outlet, NavLink, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Home, Leaf, Bot, CloudSun, Languages, User, Sparkles } from 'lucide-react';

export default function Layout() {
  const { t, i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'ta' : 'en';
    i18n.changeLanguage(newLang);
  };

  const navItems = [
    { to: "/dashboard", label: t('home'), icon: Home },
    { to: "/crop", label: t('crop'), icon: Leaf, highlight: true },
    { to: "/assistant", label: t('ai'), icon: Bot },
    { to: "/weather", label: t('weather') || "Weather", icon: CloudSun },
  ];

  return (
    <div className="flex flex-col min-h-screen bg-[#F8FAF9] text-[#16352A]">
      {/* Top Header (Desktop & Mobile) */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-gray-100/80 transition-all shadow-xs">
        <div className="flex justify-between items-center px-4 md:px-8 py-3.5 max-w-5xl mx-auto w-full">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-2.5 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-green-700 flex items-center justify-center text-white shadow-sm shadow-emerald-700/20 group-hover:scale-105 transition-transform">
              <Leaf size={22} className="fill-current text-white/90" />
            </div>
            <div>
              <span className="text-xl font-extrabold tracking-tight text-agronex-deep flex items-center gap-1.5 font-display">
                AgroNex
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200/50">
                  AI
                </span>
              </span>
              <p className="text-[10px] text-gray-500 font-medium hidden sm:block -mt-0.5">
                Smart Crop Protection
              </p>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1.5 bg-gray-50/80 p-1.5 rounded-2xl border border-gray-100">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-sm font-semibold transition-all ${
                      isActive
                        ? 'bg-white text-agronex-deep shadow-xs border border-gray-100 font-bold'
                        : 'text-gray-600 hover:text-agronex-deep hover:bg-white/60'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon size={17} className={isActive ? 'text-agronex-primary' : 'text-gray-400'} />
                      <span>{item.label}</span>
                      {isActive && (
                        <span className="w-1.5 h-1.5 rounded-full bg-agronex-primary animate-pulse" />
                      )}
                    </>
                  )}
                </NavLink>
              );
            })}
          </nav>

          {/* Right Action: Language Switcher */}
          <div className="flex items-center gap-2.5">
            <button 
              onClick={toggleLanguage}
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 bg-emerald-50/80 border border-emerald-200/60 text-emerald-900 rounded-full hover:bg-emerald-100 hover:scale-105 active:scale-95 transition-all shadow-xs"
              title="Change Language"
            >
              <Languages size={14} className="text-emerald-700" />
              <span>{i18n.language === 'en' ? 'தமிழ்' : 'English'}</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-grow max-w-5xl mx-auto w-full px-4 sm:px-6 pt-5 pb-24 md:pb-12">
        <Outlet />
      </main>

      {/* Mobile Floating Bottom Navigation Dock */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-lg border-t border-gray-100 shadow-[0_-4px_24px_rgba(0,0,0,0.06)] px-3 py-2 flex justify-around items-center">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center py-1 px-3 rounded-2xl transition-all relative ${
                  isActive
                    ? 'text-agronex-deep font-bold scale-105'
                    : 'text-gray-400 hover:text-gray-600'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <div
                    className={`w-10 h-7 rounded-full flex items-center justify-center transition-all ${
                      isActive ? 'bg-emerald-100 text-emerald-800 shadow-xs' : ''
                    }`}
                  >
                    <Icon size={20} className={isActive ? 'text-emerald-800' : 'text-gray-500'} />
                  </div>
                  <span className={`text-[11px] mt-0.5 tracking-tight ${isActive ? 'font-bold text-agronex-deep' : 'font-medium'}`}>
                    {item.label}
                  </span>
                </>
              )}
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}

