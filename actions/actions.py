# Rasa va boshqa kerakli kutubxonalarni import qilish
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
import PyPDF2
import re  # Matn ichidan so'z qidirish uchun

# --- Global Sozlamalar ---

# BU YERGA GOOGLE AI STUDIO'DAN OLGAN API KALITINGIZNI JOYLANG
GOOGLE_API_KEY = 'AIzaSyB42qZrrqyUZ8CeUgIkjLFvQv3j3VXCuRQ' 
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"

# Loyihangizdagi PDF fayl nomi
PDF_FILE_PATH = 'institut_malumot.pdf'

# --- PDF'dan Ma'lumot Qidirish Uchun Action ---

class ActionGetInstituteInfo(Action):
    """Institut haqidagi PDF fayldan ma'lumot qidirib, foydalanuvchiga javob beradi."""
    def name(self) -> Text:
        return "action_get_institute_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Foydalanuvchi aynan nima haqida so'raganini topishga harakat qilamiz (keyinchalik buni entitylar bilan qilamiz)
        user_message = tracker.latest_message.get('text').lower()
        keyword = None
        
        if 'fakultet' in user_message:
            keyword = 'fakultet'
        elif 'kafedra' in user_message:
            keyword = 'kafedra'
        elif 'rektor' in user_message:
            keyword = 'rektor'

        try:
            full_text = ""
            with open(PDF_FILE_PATH, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    full_text += page.extract_text() + "\n"
            
            if keyword:
                # Matndan kalit so'zga oid gaplarni topish
                # re.IGNORECASE - katta-kichik harflarni farqlamaslik
                sentences = re.findall(f"[^.!?]*{keyword}[^.!?]*[.!?]", full_text, re.IGNORECASE)
                if sentences:
                    # Topilgan birinchi gapni javob qilib beramiz
                    response_text = "PDF fayldan quyidagi ma'lumotni topdim: " + " ".join(sentences).strip()
                else:
                    response_text = f"Kechirasiz, PDF fayldan '{keyword}' haqida aniq ma'lumot topa olmadim."
            else:
                response_text = "Institut haqidagi ma'lumotlar fayli mavjud. Aniqroq nima haqida bilmoqchisiz (masalan, 'fakultetlar' yoki 'rektorat')?"

        except FileNotFoundError:
            response_text = f"Kechirasiz, '{PDF_FILE_PATH}' nomli ma'lumotlar fayli topilmadi."
        except Exception as e:
            response_text = f"Kechirasiz, PDF faylni o'qishda kutilmagan xatolik yuz berdi: {e}"

        dispatcher.utter_message(text=response_text)
        return []


# --- Generativ AI (Gemini) Bilan Suhbatlashish Uchun Action ---

class ActionGenerativeAnswer(Action):
    """Agar bot savolni tushunmasa, Gemini'ga murojaat qilib, ijodiy javob beradi."""
    def name(self) -> Text:
        return "action_generative_answer"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        user_question = tracker.latest_message.get('text')
        
        # Gemini'ga o'z rolini tushuntirib, savolni yuboramiz
        prompt = f"Sen O'zbekistondagi nufuzli [Institut Nomi] uchun yaratilgan, 'Adti-dasturchi' ismli aqlli, xushmuomala va yordam berishga tayyor virtual yordamchisan. Hech qachon o'zingni til modeli yoki Gemini deb tanishtirma. Foydalanuvchining quyidagi savoliga o'zbek tilida, do'stona va ilmiy ohangda javob ber: '{user_question}'"

        response_text = "Kechirasiz, hozir bu savolingizga javob bera olmayman. Institut faoliyatiga oid savollaringiz bo'lsa, marhamat."

        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        try:
            # Google serveriga POST so'rovini yuborish
            response = requests.post(GEMINI_API_URL, json=payload, timeout=20)
            response.raise_for_status()
            
            result = response.json()
            # Ba'zan 'candidates' bo'lmasligi mumkin, shuni tekshiramiz
            if 'candidates' in result and result['candidates']:
                response_text = result['candidates'][0]['content']['parts'][0]['text']
            else:
                # Agar Gemini xavfsizlik sababli javob bermasa
                response_text = "Bu mavzuda suhbatlasha olmayman. Keling, institut haqida gaplashamiz."

        except requests.exceptions.RequestException as e:
            print(f"Internetga ulanishda xatolik: {e}")
            response_text = "Internetga ulanishda muammo yuzaga keldi. Iltimos, birozdan so'ng qayta urinib ko'ring."
        except Exception as e:
            print(f"Generativ AI bilan ishlashda kutilmagan xatolik: {e}")

        dispatcher.utter_message(text=response_text)
        return []