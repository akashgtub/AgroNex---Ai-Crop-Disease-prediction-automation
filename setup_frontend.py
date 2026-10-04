import os

frontend_dir = "c:/AgroNex/frontend/src"
dirs = ["components", "pages", "services"]

for d in dirs:
    os.makedirs(os.path.join(frontend_dir, d), exist_ok=True)

components = {
    "Layout.jsx": """import { Outlet, Link } from 'react-router-dom';
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
"""
}

pages = {
    "Home.jsx": """import { useTranslation } from 'react-i18next';
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
""",
    "Login.jsx": """import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { Leaf } from 'lucide-react';

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

        <div className="mt-6 flex justify-center gap-4">
          <button className="w-12 h-12 rounded-full border border-gray-200 flex items-center justify-center hover:bg-gray-50 transition-colors">
            <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" className="w-6 h-6" />
          </button>
        </div>
        
        <p className="text-center mt-8 text-sm text-gray-500">
          {t('dont_have_account').split('?')[0]}? <Link to="/register" className="text-agronex-primary font-bold">{t('dont_have_account').split('?')[1]}</Link>
        </p>
      </div>
    </div>
  );
}
""",
    "Dashboard.jsx": """import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Camera, Upload, Leaf, Bot, FileText, CloudSun } from 'lucide-react';

export default function Dashboard() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6 pb-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-agronex-deep">{t('good_morning')}</h1>
      </div>
      
      <p className="text-gray-500 font-medium">{t('my_farm')}</p>

      {/* Main CTA */}
      <div className="bg-agronex-deep rounded-3xl p-6 text-white shadow-lg relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2 text-agronex-bright">
            <Leaf size={24} />
            <h2 className="text-xl font-bold">{t('check_crop_title').toUpperCase()}</h2>
          </div>
          <p className="text-green-100 mb-6">{t('take_photo')} or {t('upload_image').toLowerCase()}</p>
          
          <div className="flex gap-3">
            <Link to="/crop" className="flex-1 bg-agronex-primary hover:bg-green-500 py-3 rounded-xl flex justify-center items-center gap-2 font-medium transition-colors">
              <Camera size={20} />
              Photo
            </Link>
            <Link to="/crop" className="flex-1 bg-white/20 hover:bg-white/30 backdrop-blur-sm py-3 rounded-xl flex justify-center items-center gap-2 font-medium transition-colors">
              <Upload size={20} />
              Upload
            </Link>
          </div>
        </div>
        {/* Background decorative circles */}
        <div className="absolute -right-8 -bottom-8 w-40 h-40 bg-white/10 rounded-full blur-xl pointer-events-none"></div>
        <div className="absolute top-0 right-10 w-20 h-20 bg-green-400/20 rounded-full blur-lg pointer-events-none"></div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { icon: <Camera size={24} />, label: t('crop'), to: "/crop", color: "bg-green-100 text-green-700" },
          { icon: <Bot size={24} />, label: t('ai'), to: "/assistant", color: "bg-blue-100 text-blue-700" },
          { icon: <Leaf size={24} />, label: "Crops", to: "/knowledge", color: "bg-orange-100 text-orange-700" },
          { icon: <FileText size={24} />, label: t('reports'), to: "/history", color: "bg-purple-100 text-purple-700" },
        ].map((item, idx) => (
          <Link key={idx} to={item.to} className="flex flex-col items-center justify-center bg-white p-4 rounded-2xl shadow-sm border border-gray-50 hover:shadow-md transition-all">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-2 ${item.color}`}>
              {item.icon}
            </div>
            <span className="text-xs font-medium text-gray-600">{item.label}</span>
          </Link>
        ))}
      </div>

      {/* Recent Crops */}
      <div>
        <h3 className="text-lg font-bold text-agronex-deep mb-3">{t('recent_health')}</h3>
        <div className="space-y-3">
          <div className="bg-white p-4 rounded-2xl flex items-center gap-4 shadow-sm border border-gray-100">
            <div className="w-16 h-16 bg-green-50 rounded-xl flex-shrink-0 flex items-center justify-center overflow-hidden">
              <span className="text-3xl">🍅</span>
            </div>
            <div className="flex-grow">
              <h4 className="font-bold text-gray-800">Tomato</h4>
              <p className="text-sm text-green-600 font-medium">Health: Good</p>
            </div>
            <div className="text-xs text-gray-400 text-right">
              Today
            </div>
          </div>
          
          <div className="bg-white p-4 rounded-2xl flex items-center gap-4 shadow-sm border border-gray-100">
            <div className="w-16 h-16 bg-amber-50 rounded-xl flex-shrink-0 flex items-center justify-center overflow-hidden">
              <span className="text-3xl">🌾</span>
            </div>
            <div className="flex-grow">
              <h4 className="font-bold text-gray-800">Paddy</h4>
              <p className="text-sm text-amber-600 font-medium">Risk: Medium</p>
            </div>
            <div className="text-xs text-gray-400 text-right">
              2 days ago
            </div>
          </div>
        </div>
      </div>

      {/* Advisory */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-5 rounded-2xl border border-blue-100">
        <div className="flex items-center gap-2 mb-2 text-blue-800">
          <CloudSun size={20} />
          <h3 className="font-bold">{t('todays_advice')}</h3>
        </div>
        <p className="text-sm text-blue-900 leading-relaxed">
          High humidity expected today. Monitor your tomato crops carefully for signs of fungal disease.
        </p>
      </div>
    </div>
  );
}
""",
    "CropCheck.jsx": """import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Camera, Image as ImageIcon, CheckCircle, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function CropCheck() {
  const { t } = useTranslation();
  const [image, setImage] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const navigate = useNavigate();

  const handleImageUpload = (e) => {
    if (e.target.files && e.target.files[0]) {
      const img = URL.createObjectURL(e.target.files[0]);
      setImage(img);
    }
  };

  const analyze = () => {
    setAnalyzing(true);
    // Simulate API call
    setTimeout(() => {
      setAnalyzing(false);
      navigate('/result');
    }, 2000);
  };

  return (
    <div className="space-y-6 max-w-lg mx-auto">
      <div className="text-center mt-4">
        <h1 className="text-3xl font-bold text-agronex-deep mb-2">{t('check_crop_title')}</h1>
        <p className="text-gray-500">{t('check_crop_subtitle')}</p>
      </div>

      {!image ? (
        <div className="mt-8">
          <div className="border-2 border-dashed border-agronex-primary/40 bg-agronex-soft rounded-3xl p-12 text-center transition-all hover:bg-green-50/80">
            <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm text-agronex-primary">
              <Camera size={40} />
            </div>
            
            <label className="block mb-3">
              <span className="bg-agronex-primary hover:bg-agronex-deep cursor-pointer text-white px-8 py-3 rounded-xl font-bold inline-block transition-colors">
                {t('take_photo')}
              </span>
              <input type="file" accept="image/*" capture="environment" className="hidden" onChange={handleImageUpload} />
            </label>
            
            <label className="block">
              <span className="text-agronex-primary font-medium hover:underline cursor-pointer flex items-center justify-center gap-2">
                <ImageIcon size={18} /> {t('upload_image')}
              </span>
              <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
            </label>
          </div>

          <div className="mt-8 bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
            <h3 className="font-bold text-gray-800 mb-3">{t('instructions')}</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-green-500" /> {t('inst_1')}</li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-green-500" /> {t('inst_2')}</li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-green-500" /> {t('inst_3')}</li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-green-500" /> {t('inst_4')}</li>
            </ul>
          </div>
        </div>
      ) : (
        <div className="mt-8 animate-in fade-in zoom-in duration-300">
          <div className="relative rounded-3xl overflow-hidden shadow-lg border-4 border-white">
            <img src={image} alt="Crop preview" className="w-full h-80 object-cover" />
            
            {analyzing && (
              <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex flex-col items-center justify-center">
                <div className="w-16 h-16 border-4 border-agronex-soft border-t-agronex-primary rounded-full animate-spin mb-4"></div>
                <p className="font-bold text-agronex-deep text-lg">🌱 AgroNex is checking your crop...</p>
              </div>
            )}
          </div>
          
          <div className="flex gap-4 mt-6">
            <button 
              onClick={() => setImage(null)}
              disabled={analyzing}
              className="flex-1 bg-white border border-gray-200 text-gray-700 py-4 rounded-xl font-bold hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              {t('retake_photo')}
            </button>
            <button 
              onClick={analyze}
              disabled={analyzing}
              className="flex-1 bg-agronex-primary text-white py-4 rounded-xl font-bold hover:bg-agronex-deep transition-colors shadow-md disabled:opacity-50"
            >
              {t('analyze_crop')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
""",
    "Result.jsx": """import { useTranslation } from 'react-i18next';
import { ShieldAlert, AlertTriangle, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Result() {
  const { t } = useTranslation();

  return (
    <div className="max-w-lg mx-auto pb-10">
      <Link to="/dashboard" className="inline-flex items-center text-gray-500 hover:text-agronex-deep mb-4 font-medium transition-colors">
        <ArrowLeft size={20} className="mr-1" /> Back to Dashboard
      </Link>

      <div className="bg-white rounded-3xl overflow-hidden shadow-sm border border-red-100">
        <div className="bg-red-50 p-6 text-center border-b border-red-100">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 text-red-600 rounded-full mb-3 shadow-sm">
            <ShieldAlert size={32} />
          </div>
          <h1 className="text-2xl font-bold text-red-800 mb-1">{t('analysis_result')}</h1>
          <p className="text-red-600 font-medium">{t('status')}: At Risk</p>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-gray-50 p-4 rounded-2xl">
              <p className="text-xs text-gray-500 uppercase tracking-wider font-bold mb-1">Crop</p>
              <p className="font-bold text-gray-900">Tomato</p>
            </div>
            <div className="bg-red-50 p-4 rounded-2xl">
              <p className="text-xs text-red-500 uppercase tracking-wider font-bold mb-1">{t('detected_condition')}</p>
              <p className="font-bold text-red-700">Early Blight</p>
            </div>
            <div className="bg-green-50 p-4 rounded-2xl">
              <p className="text-xs text-green-600 uppercase tracking-wider font-bold mb-1">{t('confidence')}</p>
              <p className="font-bold text-green-800 text-xl">94%</p>
            </div>
            <div className="bg-orange-50 p-4 rounded-2xl">
              <p className="text-xs text-orange-600 uppercase tracking-wider font-bold mb-1">{t('severity')}</p>
              <p className="font-bold text-orange-800">Moderate</p>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="font-bold text-lg text-agronex-deep mb-2 flex items-center gap-2">
               {t('why_detected')}
            </h3>
            <p className="text-gray-600 text-sm leading-relaxed bg-gray-50 p-4 rounded-xl border border-gray-100">
              The AI detected characteristic concentric rings and dark spots with yellow halos on the lower leaves, which are strong visual indicators of Early Blight caused by Alternaria solani.
            </p>
          </div>

          <div>
            <h3 className="font-bold text-lg text-agronex-deep mb-2 flex items-center gap-2">
              {t('what_to_do')}
            </h3>
            <ul className="space-y-3 bg-agronex-soft p-4 rounded-xl border border-green-100">
              <li className="flex items-start gap-3">
                <span className="bg-agronex-primary text-white w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold mt-0.5">1</span>
                <p className="text-sm text-gray-800">Remove and destroy infected lower leaves immediately to prevent spread.</p>
              </li>
              <li className="flex items-start gap-3">
                <span className="bg-agronex-primary text-white w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold mt-0.5">2</span>
                <p className="text-sm text-gray-800">Apply a copper-based fungicide or chlorothalonil according to label instructions.</p>
              </li>
              <li className="flex items-start gap-3">
                <span className="bg-agronex-primary text-white w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold mt-0.5">3</span>
                <p className="text-sm text-gray-800">Ensure proper spacing between plants to improve air circulation.</p>
              </li>
            </ul>
          </div>
          
          <div className="mt-8">
             <button className="w-full bg-agronex-primary hover:bg-agronex-deep text-white font-bold py-4 rounded-xl shadow-md transition-colors">
               Save Report
             </button>
          </div>
        </div>
      </div>
    </div>
  );
}
""",
    "Assistant.jsx": """import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Send, Mic, Bot, User } from 'lucide-react';

export default function Assistant() {
  const { t, i18n } = useTranslation();
  const [messages, setMessages] = useState([
    { id: 1, type: 'ai', text: i18n.language === 'en' ? "Hello! I'm AgroNex AI. How can I help you with your farm today?" : "வணக்கம்! நான் அக்ரோநெக்ஸ் AI. இன்று உங்கள் பண்ணைக்கு நான் எப்படி உதவ முடியும்?" }
  ]);
  const [input, setInput] = useState('');
  
  const sendMessage = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    // Add user message
    const newMessages = [...messages, { id: Date.now(), type: 'user', text: input }];
    setMessages(newMessages);
    setInput('');
    
    // Simulate AI response
    setTimeout(() => {
      setMessages([...newMessages, { 
        id: Date.now() + 1, 
        type: 'ai', 
        text: i18n.language === 'en' ? "This is a mock response from the AI backend. Your message was: " + input : "இது AI இலிருந்து வரும் மாதிரிப் பதில். உங்கள் செய்தி: " + input 
      }]);
    }, 1000);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] md:h-[calc(100vh-100px)] bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="bg-agronex-deep text-white p-4 flex items-center gap-3">
        <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
          <Bot size={24} />
        </div>
        <div>
          <h2 className="font-bold text-lg leading-tight">{t('ask_ai_title')}</h2>
          <p className="text-green-100 text-xs">{t('ask_ai_subtitle')}</p>
        </div>
      </div>
      
      <div className="flex-grow p-4 overflow-y-auto space-y-4 bg-gray-50/50">
        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'} gap-2`}>
            {msg.type === 'ai' && (
               <div className="w-8 h-8 bg-agronex-primary rounded-full flex items-center justify-center text-white flex-shrink-0 mt-1">
                 <Bot size={16} />
               </div>
            )}
            <div className={`max-w-[75%] p-3 rounded-2xl text-sm ${msg.type === 'user' ? 'bg-agronex-primary text-white rounded-tr-sm' : 'bg-white border border-gray-100 text-gray-800 shadow-sm rounded-tl-sm'}`}>
              {msg.text}
            </div>
            {msg.type === 'user' && (
               <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center text-gray-600 flex-shrink-0 mt-1">
                 <User size={16} />
               </div>
            )}
          </div>
        ))}
      </div>
      
      <div className="p-3 bg-white border-t border-gray-100">
        <form onSubmit={sendMessage} className="flex gap-2 bg-gray-100 p-1 pl-4 rounded-full items-center">
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t('type_message')}
            className="flex-grow bg-transparent border-none outline-none text-gray-700 text-sm"
          />
          <button type="button" className="p-2 text-gray-500 hover:text-agronex-primary transition-colors">
            <Mic size={20} />
          </button>
          <button type="submit" className="p-2 bg-agronex-primary text-white rounded-full hover:bg-agronex-deep transition-colors">
            <Send size={18} className="ml-1" />
          </button>
        </form>
      </div>
    </div>
  );
}
"""
}

for name, content in components.items():
    with open(os.path.join(frontend_dir, "components", name), "w", encoding="utf-8") as f:
        f.write(content)

for name, content in pages.items():
    with open(os.path.join(frontend_dir, "pages", name), "w", encoding="utf-8") as f:
        f.write(content)

# create App.jsx and main.jsx
app_jsx = """import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CropCheck from './pages/CropCheck';
import Result from './pages/Result';
import Assistant from './pages/Assistant';
import './i18n/i18n';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="login" element={<Login />} />
          <Route path="register" element={<Login />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="crop" element={<CropCheck />} />
          <Route path="result" element={<Result />} />
          <Route path="assistant" element={<Assistant />} />
          {/* Add more routes here */}
          <Route path="*" element={<Dashboard />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
"""

with open(os.path.join(frontend_dir, "App.jsx"), "w", encoding="utf-8") as f:
    f.write(app_jsx)
