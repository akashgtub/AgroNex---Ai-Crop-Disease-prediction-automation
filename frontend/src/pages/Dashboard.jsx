import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Camera, Upload, Leaf, Bot, CloudSun, Sparkles, ArrowRight, ShieldCheck, Activity } from 'lucide-react';
import LocationWeatherCard from '../components/LocationWeatherCard';

export default function Dashboard() {
  const { t, i18n } = useTranslation();
  const isTamil = i18n.language === 'ta';

  const getTimeGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return isTamil ? "இனிய காலை வணக்கம்" : "Good Morning";
    if (hour < 17) return isTamil ? "இனிய மதிய வணக்கம்" : "Good Afternoon";
    return isTamil ? "இனிய மாலை வணக்கம்" : "Good Evening";
  };

  return (
    <div className="space-y-6 pb-6">
      {/* Header Greeting Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-800">
              {isTamil ? "அக்ரோநெக்ஸ் ஸ்மார்ட் பண்ணை" : "AgroNex Smart Farm"}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-agronex-deep font-display mt-0.5">
            {getTimeGreeting()}, {isTamil ? "விவசாயி" : "Farmer"}!
          </h1>
        </div>

        {/* Live System Status Pill */}
        <div className="flex items-center gap-2 bg-white px-3.5 py-1.5 rounded-full border border-gray-100 shadow-xs self-start sm:self-auto">
          <Activity size={14} className="text-emerald-600" />
          <span className="text-xs font-semibold text-gray-600">
            AI Engine: <strong className="text-emerald-700 font-bold">Online</strong>
          </span>
        </div>
      </div>

      {/* Main Hero Diagnostic Card */}
      <div className="relative rounded-3xl overflow-hidden shadow-lg bg-gradient-to-br from-[#0B5D3B] via-[#0f7249] to-[#16A36A] p-6 sm:p-8 text-white">
        {/* Glow ambient background lights */}
        <div className="absolute -right-10 -bottom-10 w-60 h-60 bg-white/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -top-12 right-20 w-44 h-44 bg-emerald-400/20 rounded-full blur-2xl pointer-events-none" />

        <div className="relative z-10 max-w-xl">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/15 backdrop-blur-md text-emerald-100 text-xs font-semibold mb-3 border border-white/20">
            <Sparkles size={13} className="text-emerald-300" />
            <span>{isTamil ? "உடனடி AI நோய் கண்டறிதல்" : "Instant AI Crop Diagnosis"}</span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black font-display tracking-tight leading-tight mb-2">
            {isTamil ? "பயிர் இலையை ஸ்கேன் செய்து நோயைக் கண்டறியவும்" : "Detect Crop Disease with AI"}
          </h2>
          <p className="text-emerald-100/90 text-sm leading-relaxed mb-6 font-medium">
            {isTamil 
              ? "பாதிக்கப்பட்ட பயிர் இலையின் புகைப்படத்தை எடுத்து உடனடி தீர்வு மற்றும் உர ஆலோசனையைப் பெறுங்கள்." 
              : "Snap a photo of the affected plant leaf to receive immediate disease diagnosis & treatment guidelines."}
          </p>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <Link 
              to="/crop" 
              className="bg-white hover:bg-emerald-50 text-agronex-deep font-bold px-6 py-3.5 rounded-2xl flex items-center justify-center gap-2 shadow-md hover:scale-[1.02] active:scale-[0.98] transition-all text-sm group"
            >
              <Camera size={19} className="text-emerald-700" />
              <span>{isTamil ? "புகைப்படம் எடுக்கவும்" : "Take Leaf Photo"}</span>
              <ArrowRight size={16} className="text-emerald-600 group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link 
              to="/crop" 
              className="bg-white/15 hover:bg-white/25 backdrop-blur-md border border-white/25 text-white font-semibold px-5 py-3.5 rounded-2xl flex items-center justify-center gap-2 transition-all text-sm"
            >
              <Upload size={18} />
              <span>{isTamil ? "கேலரியிலிருந்து பதிவேற்று" : "Upload Image"}</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Quick Action Highlights */}
      <div>
        <div className="flex items-center justify-between mb-3 px-1">
          <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider">
            {isTamil ? "முக்கிய சேவைகள்" : "Essential Tools"}
          </h3>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
          {[
            { 
              icon: <Camera size={22} />, 
              title: t('crop'), 
              desc: isTamil ? "நோய் ஸ்கேன்" : "Health Scan", 
              to: "/crop", 
              iconBg: "bg-emerald-100 text-emerald-800",
              border: "hover:border-emerald-300"
            },
            { 
              icon: <Bot size={22} />, 
              title: t('ai'), 
              desc: isTamil ? "குரல் உதவியாளர்" : "Sarvam AI Voice", 
              to: "/assistant", 
              iconBg: "bg-blue-100 text-blue-800",
              badge: "Voice",
              border: "hover:border-blue-300"
            },
            { 
              icon: <CloudSun size={22} />, 
              title: isTamil ? "வானிலை" : "Weather", 
              desc: isTamil ? "மழை கணிப்பு" : "Rain & Wind", 
              to: "/weather", 
              iconBg: "bg-amber-100 text-amber-800",
              border: "hover:border-amber-300"
            },
            { 
              icon: <ShieldCheck size={22} />, 
              title: isTamil ? "அறிக்கைகள்" : "Advisories", 
              desc: isTamil ? "பாதுகாப்பு" : "Field Protection", 
              to: "/crop", 
              iconBg: "bg-purple-100 text-purple-800",
              border: "hover:border-purple-300"
            },
          ].map((item, idx) => (
            <Link 
              key={idx} 
              to={item.to} 
              className={`bg-white p-4 rounded-2xl border border-gray-100 shadow-xs hover:shadow-md transition-all flex flex-col justify-between group relative overflow-hidden ${item.border}`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className={`w-11 h-11 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110 ${item.iconBg}`}>
                  {item.icon}
                </div>
                {item.badge && (
                  <span className="text-[10px] font-extrabold px-1.5 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200/60 uppercase">
                    {item.badge}
                  </span>
                )}
              </div>
              <div>
                <h4 className="font-bold text-gray-900 text-sm group-hover:text-agronex-primary transition-colors">
                  {item.title}
                </h4>
                <p className="text-[11px] text-gray-500 font-medium">
                  {item.desc}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Live Location Weather Card */}
      <LocationWeatherCard />
    </div>
  );
}

