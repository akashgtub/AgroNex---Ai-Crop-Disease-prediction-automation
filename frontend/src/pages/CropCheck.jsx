import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Camera, Image as ImageIcon, CheckCircle, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function CropCheck() {
  const { t } = useTranslation();
  const [image, setImage] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const navigate = useNavigate();

  const [fileObj, setFileObj] = useState(null);

  const handleImageUpload = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setFileObj(file);
      const img = URL.createObjectURL(file);
      setImage(img);
    }
  };

  const analyze = async () => {
    if (!fileObj) return;
    setAnalyzing(true);
    setErrorMsg(null);
    
    const formData = new FormData();
    formData.append('file', fileObj);
    
    try {
      const response = await fetch('http://localhost:8000/api/crops/analyze', {
        method: 'POST',
        body: formData,
      });
      
      if (response.ok) {
        const data = await response.json();
        navigate('/result', { state: { result: data, imageUrl: image } });
      } else {
        console.error('Analysis failed', response.statusText);
        setErrorMsg("Unable to analyze this image.");
      }
    } catch (error) {
      console.error('API Error:', error);
      setErrorMsg("Unable to analyze this image.");
    } finally {
      setAnalyzing(false);
    }
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
                <p className="font-bold text-agronex-deep text-lg">Analyzing...</p>
              </div>
            )}
          </div>
          
          {errorMsg && (
            <div className="mt-6 bg-red-50 p-4 rounded-xl text-center border border-red-100">
              <p className="text-red-600 font-bold mb-2">{errorMsg}</p>
              <button 
                onClick={() => setErrorMsg(null)}
                className="bg-red-100 text-red-700 px-6 py-2 rounded-lg font-medium hover:bg-red-200 transition-colors"
              >
                Try Again
              </button>
            </div>
          )}

          {!errorMsg && (
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
          )}
        </div>
      )}
    </div>
  );
}
