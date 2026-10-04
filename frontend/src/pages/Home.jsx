import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { 
  Leaf, 
  Bot, 
  Sparkles, 
  ShieldCheck, 
  CloudSun, 
  Mic, 
  ArrowRight,
  CheckCircle2,
  Activity
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function Home() {
  const { t, i18n } = useTranslation();

  return (
    <div className="min-h-[85vh] flex flex-col justify-between py-6 md:py-12 space-y-12 max-w-5xl mx-auto">
      {/* Hero Header */}
      <div className="flex flex-col items-center text-center space-y-6">
        {/* Top Innovation Pill */}
        <motion.div 
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-50 border border-emerald-200/80 text-emerald-800 text-xs md:text-sm font-semibold shadow-xs"
        >
          <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>{i18n.language === 'ta' ? 'அடுத்த தலைமுறை வேளாண் நுண்ணறிவு' : 'Next-Gen Precision Agri AI Platform'}</span>
          <Sparkles size={14} className="text-emerald-600" />
        </motion.div>

        {/* Brand Icon & Heading */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col items-center space-y-4"
        >
          <div className="relative">
            <div className="w-20 h-20 md:w-24 md:h-24 rounded-3xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-white transform hover:rotate-3 transition-transform">
              <Leaf size={46} className="text-white drop-shadow-sm" />
            </div>
            <div className="absolute -bottom-1 -right-1 bg-white p-1 rounded-full shadow-md">
              <Activity size={16} className="text-emerald-600 animate-pulse" />
            </div>
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-slate-900 tracking-tight font-display">
            {t('app_name')}
          </h1>

          <p className="text-lg sm:text-xl font-semibold bg-gradient-to-r from-emerald-700 via-teal-700 to-emerald-600 bg-clip-text text-transparent max-w-xl">
            {t('tagline')}
          </p>
        </motion.div>

        {/* Narrative Description */}
        <p className="text-slate-600 max-w-2xl text-base md:text-lg leading-relaxed">
          {t('hero_desc')}
        </p>

        {/* Primary Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-3.5 w-full max-w-md pt-2">
          <Link 
            to="/crop" 
            className="w-full sm:flex-1 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white py-4 px-6 rounded-2xl font-bold flex items-center justify-center gap-2.5 transition-all shadow-md hover:shadow-xl hover:shadow-emerald-600/25 active:scale-[0.98]"
          >
            <Leaf size={20} />
            <span>{t('check_my_crop')}</span>
            <ArrowRight size={18} />
          </Link>
          <Link 
            to="/assistant" 
            className="w-full sm:flex-1 bg-white hover:bg-emerald-50/60 text-slate-800 border border-slate-200 hover:border-emerald-300 py-4 px-6 rounded-2xl font-bold flex items-center justify-center gap-2.5 transition-all shadow-xs hover:shadow-md active:scale-[0.98]"
          >
            <Bot size={20} className="text-emerald-600" />
            <span>{t('ask_agronex')}</span>
          </Link>
        </div>

        {/* Auth Quick Links */}
        <div className="flex items-center gap-2 text-sm text-slate-500 pt-1">
          <Link to="/dashboard" className="text-emerald-700 font-semibold hover:underline flex items-center gap-1">
            <span>{i18n.language === 'ta' ? 'டாஷ்போர்டுக்கு செல்க' : 'Go to Dashboard'}</span>
            <ArrowRight size={13} />
          </Link>
          <span className="text-slate-300">•</span>
          <Link to="/login" className="text-slate-600 hover:text-emerald-700 font-medium transition-colors">
            {t('login')}
          </Link>
          <span className="text-slate-300">•</span>
          <Link to="/register" className="text-slate-600 hover:text-emerald-700 font-medium transition-colors">
            {t('register')}
          </Link>
        </div>
      </div>

      {/* Feature Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-4">
        {/* Pillar 1 */}
        <div className="bg-white/80 backdrop-blur-md p-6 rounded-3xl border border-slate-100 shadow-xs hover:shadow-md transition-all space-y-3 group hover:border-emerald-200">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-105 transition-transform">
            <ShieldCheck size={24} />
          </div>
          <h3 className="font-bold text-slate-900 text-lg">
            {i18n.language === 'ta' ? 'துல்லிய நோய் கண்டறிதல்' : 'Instant Leaf Diagnosis'}
          </h3>
          <p className="text-slate-600 text-sm leading-relaxed">
            {i18n.language === 'ta' 
              ? 'பயிர் இலையை புகைப்படம் எடுத்து பதிவேற்றி வினாடிகளில் நோய் மற்றும் சிகிச்சை வழிகாட்டல் பெறலாம்.' 
              : 'Snap a live photo or upload gallery leaves. Deep CNN models identify infections with confidence scoring.'}
          </p>
          <div className="pt-2 flex items-center gap-1.5 text-xs font-semibold text-emerald-700">
            <CheckCircle2 size={14} />
            <span>{i18n.language === 'ta' ? 'உடனடி கரிம & ரசாயன தீர்வுகள்' : 'Organic & Chemical Remedies'}</span>
          </div>
        </div>

        {/* Pillar 2 */}
        <div className="bg-white/80 backdrop-blur-md p-6 rounded-3xl border border-slate-100 shadow-xs hover:shadow-md transition-all space-y-3 group hover:border-teal-200">
          <div className="w-12 h-12 rounded-2xl bg-teal-50 text-teal-600 flex items-center justify-center group-hover:scale-105 transition-transform">
            <Mic size={24} />
          </div>
          <h3 className="font-bold text-slate-900 text-lg">
            {i18n.language === 'ta' ? 'இருமொழி குரல் உதவியாளர்' : 'Bilingual Voice AI'}
          </h3>
          <p className="text-slate-600 text-sm leading-relaxed">
            {i18n.language === 'ta' 
              ? 'தமிழ் மற்றும் ஆங்கிலத்தில் பேசி பயிர் பராமரிப்பு, உரம் மற்றும் பூச்சி மேலாண்மை ஆலோசனைகளை கேட்கலாம்.' 
              : 'Powered by Sarvam Saaras STT and Bulbul TTS. Speak naturally in Tamil or English for real-time farm guidance.'}
          </p>
          <div className="pt-2 flex items-center gap-1.5 text-xs font-semibold text-teal-700">
            <CheckCircle2 size={14} />
            <span>{i18n.language === 'ta' ? 'வாய்ஸ் மெமோ & நேரலை பதில்கள்' : 'Voice Memo & Live Audio Playback'}</span>
          </div>
        </div>

        {/* Pillar 3 */}
        <div className="bg-white/80 backdrop-blur-md p-6 rounded-3xl border border-slate-100 shadow-xs hover:shadow-md transition-all space-y-3 group hover:border-cyan-200">
          <div className="w-12 h-12 rounded-2xl bg-cyan-50 text-cyan-600 flex items-center justify-center group-hover:scale-105 transition-transform">
            <CloudSun size={24} />
          </div>
          <h3 className="font-bold text-slate-900 text-lg">
            {i18n.language === 'ta' ? 'உள்ளூர் வானிலை ரேடார்' : 'Hyperlocal Weather'}
          </h3>
          <p className="text-slate-600 text-sm leading-relaxed">
            {i18n.language === 'ta' 
              ? 'மழை எச்சரிக்கை, காற்றின் வேகம் மற்றும் பூச்சி மருந்து தெளிப்புக்கான உகந்த நேர வழிகாட்டல்.' 
              : 'GPS-detected farm microclimate, 7-day agricultural radar forecasts, and smart spray window alerts.'}
          </p>
          <div className="pt-2 flex items-center gap-1.5 text-xs font-semibold text-cyan-700">
            <CheckCircle2 size={14} />
            <span>{i18n.language === 'ta' ? 'நிகழ்நேர மழை & ஈரப்பதம் கண்காணிப்பு' : 'Live Rain & Humidity Tracking'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
