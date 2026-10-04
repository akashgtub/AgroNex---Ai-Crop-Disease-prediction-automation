import { useState } from 'react';
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
