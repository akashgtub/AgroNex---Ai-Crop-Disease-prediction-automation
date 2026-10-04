import { useTranslation } from 'react-i18next';
import { ShieldAlert, AlertTriangle, ArrowLeft, CheckCircle, Bot, Sparkles, Share2, ArrowRight } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import WeatherAlerts from '../components/WeatherAlerts';

export default function Result() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const { result, imageUrl } = location.state || {};
  const isTamil = i18n.language === 'ta';

  if (!result) {
    return (
      <div className="text-center p-12 max-w-md mx-auto bg-white rounded-3xl shadow-xs border border-gray-100 my-8">
        <div className="w-16 h-16 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
          <AlertTriangle size={32} />
        </div>
        <h3 className="text-lg font-bold text-gray-800 mb-1">
          {isTamil ? "முடிவுகள் எதுவும் இல்லை" : "No Analysis Results Found"}
        </h3>
        <p className="text-gray-500 text-xs mb-6">
          {isTamil ? "தயவுசெய்து முதலில் ஒரு பயிர் இலையை ஸ்கேன் செய்யவும்." : "Please scan or upload a crop leaf photo first."}
        </p>
        <Link 
          to="/crop" 
          className="inline-flex items-center justify-center gap-2 bg-agronex-primary text-white font-bold px-6 py-3 rounded-2xl shadow-xs hover:bg-agronex-deep transition-all text-xs"
        >
          <span>{isTamil ? "பயிரை ஸ்கேன் செய்க" : "Scan a Crop Leaf"}</span>
          <ArrowRight size={14} />
        </Link>
      </div>
    );
  }

  const { crop, condition, confidence, is_healthy, top_predictions, status } = result;
  const confPercent = (confidence * 100).toFixed(1);
  const isUncertain = status === "Uncertain";
  const formattedCondition = (condition || '').replace(/_/g, ' ');

  return (
    <div className="max-w-2xl mx-auto pb-12 space-y-6">
      {/* Top Bar with Back Button */}
      <div className="flex items-center justify-between">
        <Link 
          to="/dashboard" 
          className="inline-flex items-center text-xs font-bold text-gray-500 hover:text-agronex-deep transition-colors bg-white px-3 py-1.5 rounded-full border border-gray-100 shadow-xs"
        >
          <ArrowLeft size={14} className="mr-1" />
          <span>{isTamil ? "முகப்புக்குத் திரும்பு" : "Dashboard"}</span>
        </Link>
        <span className="text-[11px] font-semibold text-gray-400">
          ID: #{Math.floor(Date.now() / 1000).toString().slice(-6)}
        </span>
      </div>

      {/* Main Diagnostic Card */}
      <div className="bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100">
        {/* Status Header Banner */}
        <div className={`p-6 sm:p-8 text-center text-white relative overflow-hidden ${
          is_healthy 
            ? 'bg-gradient-to-br from-emerald-600 to-green-700' 
            : isUncertain 
              ? 'bg-gradient-to-br from-amber-500 to-orange-600' 
              : 'bg-gradient-to-br from-rose-600 to-red-700'
        }`}>
          <div className="relative z-10">
            <div className="inline-flex items-center justify-center w-18 h-18 rounded-full bg-white/20 backdrop-blur-md mb-3 shadow-sm border border-white/30">
              {is_healthy ? (
                <CheckCircle size={38} className="text-white" />
              ) : isUncertain ? (
                <AlertTriangle size={38} className="text-white" />
              ) : (
                <ShieldAlert size={38} className="text-white" />
              )}
            </div>

            <span className="inline-block text-[11px] font-bold uppercase tracking-wider px-3 py-0.5 rounded-full bg-black/20 text-white/90 mb-2 border border-white/20">
              {isUncertain ? "Uncertain Diagnosis" : (is_healthy ? "Healthy Plant Condition" : "Plant Disease Detected")}
            </span>

            <h1 className="text-2xl sm:text-3xl font-extrabold font-display tracking-tight mb-1">
              {formattedCondition}
            </h1>
            <p className="text-white/80 text-xs font-semibold">
              {t('status')}: <strong className="text-white underline">{isUncertain ? 'Uncertain' : (is_healthy ? 'Healthy' : 'At Risk')}</strong>
            </p>
          </div>

          {/* Ambient Glow */}
          <div className="absolute -right-8 -bottom-8 w-40 h-40 bg-white/10 rounded-full blur-2xl pointer-events-none" />
        </div>

        <div className="p-6 sm:p-8 space-y-6">
          {/* Leaf Photo Preview (if available) */}
          {imageUrl && (
            <div className="relative rounded-2xl overflow-hidden shadow-xs border border-gray-100 max-h-64 bg-black/5">
              <img src={imageUrl} alt="Analyzed Crop Leaf" className="w-full h-56 object-cover" />
              <div className="absolute bottom-2.5 left-2.5 bg-black/60 backdrop-blur-md text-white text-[10px] font-bold px-2.5 py-1 rounded-full">
                📸 Inspected Leaf Sample
              </div>
            </div>
          )}

          {/* Pathology Metric Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-gray-50/80 p-3.5 rounded-2xl border border-gray-100">
              <span className="text-[10px] text-gray-400 font-extrabold uppercase tracking-wider block mb-1">Crop Type</span>
              <span className="font-bold text-gray-900 text-sm">{crop}</span>
            </div>

            <div className="bg-blue-50/80 p-3.5 rounded-2xl border border-blue-100">
              <span className="text-[10px] text-blue-600 font-extrabold uppercase tracking-wider block mb-1">AI Confidence</span>
              <span className="font-extrabold text-blue-900 text-base">{confPercent}%</span>
            </div>

            <div className="bg-emerald-50/80 p-3.5 rounded-2xl border border-emerald-100">
              <span className="text-[10px] text-emerald-700 font-extrabold uppercase tracking-wider block mb-1">Risk Level</span>
              <span className="font-bold text-emerald-900 text-sm">{is_healthy ? 'Low / None' : 'Moderate'}</span>
            </div>

            <div className="bg-amber-50/80 p-3.5 rounded-2xl border border-amber-100">
              <span className="text-[10px] text-amber-700 font-extrabold uppercase tracking-wider block mb-1">Status</span>
              <span className="font-bold text-amber-900 text-sm">{status}</span>
            </div>
          </div>

          {/* Confidence Meter Bar */}
          <div className="p-4 rounded-2xl bg-gray-50 border border-gray-100">
            <div className="flex justify-between items-center text-xs font-bold text-gray-700 mb-1.5">
              <span>Model Prediction Confidence</span>
              <span className="text-agronex-deep">{confPercent}%</span>
            </div>
            <div className="w-full bg-gray-200 h-2.5 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-1000 ${
                  confidence > 0.85 ? 'bg-emerald-500' : confidence > 0.6 ? 'bg-amber-500' : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(10, confidence * 100))}%` }}
              />
            </div>
          </div>

          {/* AI Clinical Reasoning */}
          <div>
            <h3 className="font-bold text-sm text-agronex-deep mb-2 flex items-center gap-1.5 font-display">
              <Sparkles size={16} className="text-emerald-600" />
              <span>{t('why_detected')}</span>
            </h3>
            <p className="text-gray-700 text-xs sm:text-sm leading-relaxed bg-emerald-50/60 p-4 rounded-2xl border border-emerald-100">
              {isUncertain ? (
                "AgroNex detected mixed visual traits. Please capture a closer photo in bright natural lighting for higher precision."
              ) : is_healthy ? (
                `The AI vision model verified that the leaf shows healthy chloroplast pigmentation, uniform vein patterns, and no active fungal/bacterial lesions.`
              ) : (
                `The AI model detected characteristic visual symptoms corresponding to ${formattedCondition} with ${confPercent}% confidence match.`
              )}
            </p>
          </div>

          {/* Actionable Recommendations Checklist */}
          <div>
            <h3 className="font-bold text-sm text-agronex-deep mb-2 font-display">
              {t('what_to_do')}
            </h3>
            <div className="space-y-2 bg-gray-50 p-4 rounded-2xl border border-gray-100 text-xs text-gray-700">
              <div className="flex items-start gap-2.5">
                <CheckCircle size={15} className="text-emerald-600 mt-0.5 flex-shrink-0" />
                <span>
                  {is_healthy 
                    ? "Maintain standard drip irrigation and scheduled balanced fertilizer intervals." 
                    : "Isolate heavily affected foliage to prevent spore dispersal to adjacent plants."}
                </span>
              </div>
              <div className="flex items-start gap-2.5">
                <CheckCircle size={15} className="text-emerald-600 mt-0.5 flex-shrink-0" />
                <span>
                  Check regional rainfall forecast below before applying any protective spray.
                </span>
              </div>
            </div>
          </div>

          {/* CTA: Ask AI Assistant directly */}
          <Link 
            to="/assistant" 
            className="flex items-center justify-between p-4 rounded-2xl bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 hover:border-emerald-300 transition-all shadow-xs group"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-agronex-primary text-white flex items-center justify-center shadow-xs">
                <Bot size={20} />
              </div>
              <div>
                <h4 className="font-bold text-agronex-deep text-xs sm:text-sm group-hover:text-emerald-800">
                  {isTamil ? "அக்ரோநெக்ஸ் AI உதவியாளரிடம் கேட்கவும்" : "Ask AgroNex AI for Treatment Advice"}
                </h4>
                <p className="text-[11px] text-gray-500 font-medium">
                  {isTamil ? "குரல் அல்லது உரை மூலம் உர ஆலோசனை பெறுக" : "Get spoken voice guidance & fertilizer doses"}
                </p>
              </div>
            </div>
            <ArrowRight size={18} className="text-emerald-700 group-hover:translate-x-1 transition-transform" />
          </Link>

          {/* Weather Alerts Module */}
          <div className="pt-2">
            <WeatherAlerts crop={crop} condition={condition} />
          </div>
        </div>
      </div>
    </div>
  );
}

