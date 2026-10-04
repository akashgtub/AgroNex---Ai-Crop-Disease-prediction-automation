import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Camera, Upload, Leaf, Bot, FileText, CloudSun } from 'lucide-react';
import LocationWeatherCard from '../components/LocationWeatherCard';

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

      {/* Weather Card */}
      <LocationWeatherCard />
    </div>
  );
}
