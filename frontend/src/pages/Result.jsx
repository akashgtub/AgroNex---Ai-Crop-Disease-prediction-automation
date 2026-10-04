import { useTranslation } from 'react-i18next';
import { ShieldAlert, AlertTriangle, ArrowLeft, CheckCircle } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import WeatherAlerts from '../components/WeatherAlerts';

export default function Result() {
  const { t } = useTranslation();
  const location = useLocation();
  const { result, imageUrl } = location.state || {};

  if (!result) {
    return (
      <div className="text-center p-10">
        <p>No results found. Please check a crop first.</p>
        <Link to="/crop" className="text-agronex-primary underline mt-4 block">Go back</Link>
      </div>
    );
  }

  const { crop, condition, confidence, is_healthy, top_predictions, status } = result;
  const confPercent = (confidence * 100).toFixed(1);
  const isUncertain = status === "Uncertain";

  return (
    <div className="max-w-lg mx-auto pb-10">
      <Link to="/dashboard" className="inline-flex items-center text-gray-500 hover:text-agronex-deep mb-4 font-medium transition-colors">
        <ArrowLeft size={20} className="mr-1" /> Back to Dashboard
      </Link>

      <div className={`bg-white rounded-3xl overflow-hidden shadow-sm border ${is_healthy ? 'border-green-100' : (isUncertain ? 'border-orange-100' : 'border-red-100')}`}>
        <div className={`${is_healthy ? 'bg-green-50' : (isUncertain ? 'bg-orange-50' : 'bg-red-50')} p-6 text-center border-b ${is_healthy ? 'border-green-100' : (isUncertain ? 'border-orange-100' : 'border-red-100')}`}>
          <div className={`inline-flex items-center justify-center w-16 h-16 ${is_healthy ? 'bg-green-100 text-green-600' : (isUncertain ? 'bg-orange-100 text-orange-600' : 'bg-red-100 text-red-600')} rounded-full mb-3 shadow-sm`}>
            {is_healthy ? <CheckCircle size={32} /> : (isUncertain ? <AlertTriangle size={32} /> : <ShieldAlert size={32} />)}
          </div>
          <h1 className={`text-2xl font-bold ${is_healthy ? 'text-green-800' : (isUncertain ? 'text-orange-800' : 'text-red-800')} mb-1`}>{t('analysis_result')}</h1>
          <p className={`${is_healthy ? 'text-green-600' : (isUncertain ? 'text-orange-600' : 'text-red-600')} font-medium`}>{t('status')}: {isUncertain ? 'Uncertain' : (is_healthy ? 'Healthy' : 'At Risk')}</p>
        </div>

        <div className="p-6">
          {imageUrl && (
            <div className="mb-6 rounded-2xl overflow-hidden shadow-sm">
              <img src={imageUrl} alt="Analyzed crop" className="w-full h-48 object-cover" />
            </div>
          )}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-gray-50 p-4 rounded-2xl">
              <p className="text-xs text-gray-500 uppercase tracking-wider font-bold mb-1">Crop</p>
              <p className="font-bold text-gray-900">{crop}</p>
            </div>
            <div className={`${is_healthy ? 'bg-green-50' : 'bg-red-50'} p-4 rounded-2xl`}>
              <p className={`text-xs ${is_healthy ? 'text-green-600' : 'text-red-500'} uppercase tracking-wider font-bold mb-1`}>{t('detected_condition')}</p>
              <p className={`font-bold ${is_healthy ? 'text-green-700' : 'text-red-700'}`}>{condition}</p>
            </div>
            <div className="bg-blue-50 p-4 rounded-2xl">
              <p className="text-xs text-blue-600 uppercase tracking-wider font-bold mb-1">{t('confidence')}</p>
              <p className="font-bold text-blue-800 text-xl">{confPercent}%</p>
            </div>
            <div className="bg-orange-50 p-4 rounded-2xl">
              <p className="text-xs text-orange-600 uppercase tracking-wider font-bold mb-1">Status</p>
              <p className="font-bold text-orange-800">{status}</p>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="font-bold text-lg text-agronex-deep mb-2 flex items-center gap-2">
               {t('why_detected')}
            </h3>
            <p className="text-gray-600 text-sm leading-relaxed bg-gray-50 p-4 rounded-xl border border-gray-100">
              {isUncertain ? (
                "AgroNex is not confident about this result. Please upload a clearer image."
              ) : (
                <>The AI model analyzed the visual patterns of your crop and identified <b>{condition}</b> with a confidence of {confPercent}%.</>
              )}
            </p>
          </div>

          <div>
            <h3 className="font-bold text-lg text-agronex-deep mb-2 flex items-center gap-2">
              {t('what_to_do')}
            </h3>
            <ul className="space-y-3 bg-agronex-soft p-4 rounded-xl border border-green-100">
              <li className="flex items-start gap-3">
                <p className="text-sm text-gray-800 font-medium">Guidance will be provided after validating the diagnosis.</p>
              </li>
            </ul>
          </div>
          
          <div className="mt-8">
             <button className="w-full bg-agronex-primary hover:bg-agronex-deep text-white font-bold py-4 rounded-xl shadow-md transition-colors">
               Save Report
             </button>
          </div>
          
          <div className="mt-8">
             <WeatherAlerts crop={crop} condition={condition} />
          </div>
        </div>
      </div>
    </div>
  );
}
