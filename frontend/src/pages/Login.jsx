import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { Leaf } from 'lucide-react';
import AgroNexGoogleLogin from '../features/googleAuth/GoogleLogin';

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    navigate('/dashboard');
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh]">
      <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100 w-full max-w-md">
        <div className="text-center mb-8">
          <Leaf className="text-agronex-primary mx-auto mb-2" size={40} />
          <h2 className="text-2xl font-bold text-agronex-deep">Welcome Back!</h2>
          <p className="text-agronex-secondaryText text-sm mt-1">Log in to protect your crops</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input 
              type="text" 
              placeholder={t('mobile_or_email')}
              className="w-full bg-agronex-bg border-none rounded-xl py-4 px-4 text-agronex-darkText placeholder:text-gray-400 focus:ring-2 focus:ring-agronex-primary/50 outline-none"
              required
            />
          </div>
          <div className="relative">
            <input 
              type="password" 
              placeholder={t('password')}
              className="w-full bg-agronex-bg border-none rounded-xl py-4 px-4 text-agronex-darkText placeholder:text-gray-400 focus:ring-2 focus:ring-agronex-primary/50 outline-none pr-24"
              required
            />
            <button type="button" className="absolute right-4 top-1/2 -translate-y-1/2 text-agronex-primary text-sm font-medium">
              Forgot?
            </button>
          </div>
          
          <button 
            type="submit" 
            className="w-full bg-agronex-deep hover:bg-green-900 text-white py-4 rounded-xl font-semibold flex justify-center items-center gap-2 mt-6 transition-colors shadow-sm"
          >
            {t('login')} <span className="text-xl">→</span>
          </button>
        </form>

        <div className="mt-8 flex items-center gap-4">
          <div className="h-px bg-gray-200 flex-1"></div>
          <span className="text-gray-400 text-sm">Or log in with:</span>
          <div className="h-px bg-gray-200 flex-1"></div>
        </div>

        <div className="mt-6 flex justify-center">
          <AgroNexGoogleLogin onSuccess={() => navigate('/dashboard')} />
        </div>
        
        <p className="text-center mt-8 text-sm text-gray-500">
          {t('dont_have_account').split('?')[0]}? <Link to="/register" className="text-agronex-primary font-bold">{t('dont_have_account').split('?')[1]}</Link>
        </p>
      </div>
    </div>
  );
}
