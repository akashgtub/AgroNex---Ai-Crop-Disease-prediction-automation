import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Leaf, Eye, EyeOff, Lock, Mail, User, ArrowRight, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';
import AgroNexGoogleLogin from '../features/googleAuth/GoogleLogin';

export default function Login() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();

  const isRegister = location.pathname.includes('register');
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    identifier: '',
    password: '',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    navigate('/dashboard');
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] py-8 px-4">
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white/95 backdrop-blur-md p-7 sm:p-9 rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 w-full max-w-md relative overflow-hidden"
      >
        {/* Decorative Top Accent */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-emerald-500 via-teal-500 to-emerald-600"></div>

        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-inner">
            <Leaf size={30} className="text-emerald-600" />
          </div>

          <h2 className="text-2xl font-bold text-slate-900 tracking-tight font-display">
            {isRegister
              ? (i18n.language === 'ta' ? 'புதிய கணக்கை உருவாக்கவும்' : 'Create AgroNex Account')
              : (i18n.language === 'ta' ? 'மீண்டும் வருக!' : 'Welcome Back!')
            }
          </h2>

          <p className="text-slate-500 text-xs sm:text-sm mt-1">
            {isRegister
              ? (i18n.language === 'ta' ? 'உங்கள் பயிர்களை பாதுகாக்க இப்போதே இணையுங்கள்' : 'Join AgroNex to safeguard your farm and yield')
              : (i18n.language === 'ta' ? 'உங்கள் பயிர்களை பாதுகாக்க உள்நுழையவும்' : 'Log in to protect and monitor your crops')
            }
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Optional Name field if on register route */}
          {isRegister && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 ml-1">
                {i18n.language === 'ta' ? 'முழு பெயர்' : 'Full Name'}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <User size={18} />
                </div>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder={i18n.language === 'ta' ? "உங்கள் பெயர்" : "e.g. Ramesh Kumar"}
                  className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3.5 pl-10 pr-4 text-slate-800 placeholder:text-slate-400 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none text-sm transition-all"
                  required
                />
              </div>
            </div>
          )}

          {/* Identifier field */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5 ml-1">
              {t('mobile_or_email')}
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Mail size={18} />
              </div>
              <input
                type="text"
                value={formData.identifier}
                onChange={(e) => setFormData({ ...formData, identifier: e.target.value })}
                placeholder={t('mobile_or_email')}
                className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3.5 pl-10 pr-4 text-slate-800 placeholder:text-slate-400 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none text-sm transition-all"
                required
              />
            </div>
          </div>

          {/* Password field */}
          <div>
            <div className="flex items-center justify-between mb-1.5 ml-1">
              <label className="block text-xs font-semibold text-slate-700">
                {t('password')}
              </label>
              {!isRegister && (
                <button
                  type="button"
                  onClick={() => alert(i18n.language === 'ta' ? 'கடவுச்சொல் மீட்டமைப்பு உங்கள் தொலைபேசி எண்ணிற்கு அனுப்பப்படும்.' : 'Password reset link will be sent to your mobile or email.')}
                  className="text-emerald-700 hover:text-emerald-800 text-xs font-semibold hover:underline"
                >
                  {i18n.language === 'ta' ? 'கடவுச்சொல் மறந்ததா?' : 'Forgot?'}
                </button>
              )}
            </div>

            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock size={18} />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                placeholder={t('password')}
                className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3.5 pl-10 pr-12 text-slate-800 placeholder:text-slate-400 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none text-sm transition-all"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors"
                title={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* Submit CTA */}
          <button
            type="submit"
            className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 active:scale-[0.98] text-white py-3.5 rounded-2xl font-bold flex justify-center items-center gap-2 mt-6 transition-all shadow-md shadow-emerald-600/20 text-sm"
          >
            <span>{isRegister ? t('register') : t('login')}</span>
            <ArrowRight size={17} />
          </button>
        </form>

        {/* Social Divider */}
        <div className="mt-7 flex items-center gap-3">
          <div className="h-px bg-slate-200 flex-1"></div>
          <span className="text-slate-400 text-xs uppercase tracking-wider font-medium">
            {i18n.language === 'ta' ? 'அல்லது' : 'Or continue with'}
          </span>
          <div className="h-px bg-slate-200 flex-1"></div>
        </div>

	{/* Google / Quick SSO */}
	<div className="mt-5 flex justify-center">
        <AgroNexGoogleLogin onSuccess={() => navigate('/dashboard')} />
	</div>
        </div>

        {/* Toggle between Login and Register */}
        <div className="mt-7 text-center text-xs text-slate-500">
          {isRegister ? (
            <p>
              {i18n.language === 'ta' ? 'ஏற்கனவே கணக்கு உள்ளதா? ' : 'Already have an AgroNex account? '}
              <Link to="/login" className="text-emerald-700 font-bold hover:underline">
                {t('login')}
              </Link>
            </p>
          ) : (
            <p>
              {t('dont_have_account').split('?')[0]}?{' '}
              <Link to="/register" className="text-emerald-700 font-bold hover:underline">
                {t('dont_have_account').split('?')[1] || t('register')}
              </Link>
            </p>
          )}
        </div>

        {/* Security badge */}
        <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-center gap-1.5 text-[11px] text-slate-400">
          <ShieldCheck size={14} className="text-emerald-600" />
          <span>{i18n.language === 'ta' ? 'பாதுகாப்பான விவசாய தரவு குறியாக்கம்' : '256-bit encrypted farming data'}</span>
        </div>
      </motion.div>
    </div>
  );
}
