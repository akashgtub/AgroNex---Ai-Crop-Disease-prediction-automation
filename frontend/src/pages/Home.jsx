import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Leaf, Bot } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Home() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] text-center space-y-8">
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white p-6 rounded-3xl shadow-sm border border-green-50 inline-flex flex-col items-center"
      >
        <div className="w-24 h-24 bg-agronex-soft rounded-full flex items-center justify-center mb-4">
          <Leaf size={48} className="text-agronex-primary" />
        </div>
        <h1 className="text-4xl font-bold text-agronex-deep">{t('app_name')}</h1>
        <p className="text-agronex-primary font-medium mt-2">{t('tagline')}</p>
      </motion.div>

      <p className="text-agronex-secondaryText max-w-md text-lg leading-relaxed">
        {t('hero_desc')}
      </p>

      <div className="flex flex-col sm:flex-row gap-4 w-full max-w-md mt-8">
        <Link 
          to="/crop" 
          className="flex-1 bg-agronex-primary hover:bg-agronex-deep text-white py-4 px-6 rounded-2xl font-semibold flex items-center justify-center gap-2 transition-all shadow-md hover:shadow-lg"
        >
          <Leaf size={20} />
          {t('check_my_crop')}
        </Link>
        <Link 
          to="/assistant" 
          className="flex-1 bg-white hover:bg-agronex-soft text-agronex-deep border border-agronex-primary/30 py-4 px-6 rounded-2xl font-semibold flex items-center justify-center gap-2 transition-all"
        >
          <Bot size={20} />
          {t('ask_agronex')}
        </Link>
      </div>
      
      <div className="mt-8">
        <Link to="/login" className="text-agronex-primary font-medium hover:underline">{t('login')}</Link>
        <span className="mx-2 text-gray-300">|</span>
        <Link to="/register" className="text-agronex-primary font-medium hover:underline">{t('register')}</Link>
      </div>
    </div>
  );
}
