import { Outlet, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Home, Leaf, Bot, FileText, User } from 'lucide-react';

export default function Layout() {
  const { t, i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'ta' : 'en';
    i18n.changeLanguage(newLang);
  };

  return (
    <div className="flex flex-col min-h-screen bg-agronex-bg">
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="flex justify-between items-center p-4 max-w-4xl mx-auto w-full">
          <Link to="/" className="text-xl font-bold text-agronex-deep flex items-center gap-2">
            <Leaf className="text-agronex-primary" /> AgroNex
          </Link>
          <button 
            onClick={toggleLanguage}
            className="text-sm font-medium px-3 py-1 bg-agronex-soft text-agronex-deep rounded-full hover:bg-agronex-primary hover:text-white transition-colors"
          >
            {i18n.language === 'en' ? 'தமிழ்' : 'English'}
          </button>
        </div>
      </header>

      <main className="flex-grow max-w-4xl mx-auto w-full p-4 mb-20 md:mb-0">
        <Outlet />
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white shadow-[0_-2px_10px_rgba(0,0,0,0.05)] border-t border-gray-100 flex justify-around items-center p-3 z-50">
        <Link to="/dashboard" className="flex flex-col items-center text-agronex-secondaryText hover:text-agronex-primary">
          <Home size={20} />
          <span className="text-xs mt-1">{t('home')}</span>
        </Link>
        <Link to="/crop" className="flex flex-col items-center text-agronex-secondaryText hover:text-agronex-primary">
          <Leaf size={20} />
          <span className="text-xs mt-1">{t('crop')}</span>
        </Link>
        <Link to="/assistant" className="flex flex-col items-center text-agronex-secondaryText hover:text-agronex-primary">
          <Bot size={20} />
          <span className="text-xs mt-1">{t('ai')}</span>
        </Link>
        <Link to="/history" className="flex flex-col items-center text-agronex-secondaryText hover:text-agronex-primary">
          <FileText size={20} />
          <span className="text-xs mt-1">{t('reports')}</span>
        </Link>
        <Link to="/profile" className="flex flex-col items-center text-agronex-secondaryText hover:text-agronex-primary">
          <User size={20} />
          <span className="text-xs mt-1">{t('profile')}</span>
        </Link>
      </nav>
    </div>
  );
}
