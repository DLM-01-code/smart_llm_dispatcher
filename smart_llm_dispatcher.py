import streamlit as st
import requests
import json
import base64
import os
import tempfile
from datetime import datetime
import time
import re
import subprocess

# КЛАСС УМНОГО ДИСПЕТЧЕРА

class SmartDispatcher:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.ollama_list_url = "http://localhost:11434/api/tags"
        
        #РАСШИРЕННЫЕ КАТЕГОРИИ
        self.model_categories = {
            "vision": {
                "keywords": ["vl", "vision", "llava", "paligemma", "cogvlm", "florence"],
                "emoji": "📸",
                "description": "Работа с изображениями, фото, распознавание текста"
            },
            "coding": {
                "keywords": ["coder", "code", "starcoder", "codellama", "deepseek-coder"],
                "emoji": "💻",
                "description": "Программирование, код, алгоритмы, отладка"
            },
            "reasoning": {
                "keywords": ["deepseek-r1", "reasoning", "think", "qwq"],
                "emoji": "🧠",
                "description": "Сложные рассуждения, логика, объяснения пошагово"
            },
            "math": {
                "keywords": ["math", "phi4", "qwen2.5-math", "deepseek-math"],
                "emoji": "📐",
                "description": "Математика, вычисления, логические задачи"
            },
            "general": {
                "keywords": ["llama", "qwen", "gemma", "mistral", "phi", "deepseek"],
                "emoji": "💬",
                "description": "Общие разговоры, тексты, общение, эссе"
            }
        }
        
        self.available_models = {}
        self.last_update = None
        self.conversation_history = []

    def get_installed_models(self):
        """Получает список всех моделей, установленных в Ollama"""
        try:
            response = requests.get(self.ollama_list_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                return [model["name"] for model in models]
        except:
            pass
        
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                models = []
                for line in lines[1:]:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            models.append(parts[0])
                return models
        except:
            pass
        
        return []

    def categorize_model(self, model_name):
        """Определяет категорию модели по её названию"""
        model_lower = model_name.lower()
        
        for category, info in self.model_categories.items():
            for keyword in info["keywords"]:
                if keyword in model_lower:
                    return category
        
        return "general"

    def get_model_specialization(self, model_name, category):
        """Возвращает описание специализации модели"""
        category_info = self.model_categories.get(category, self.model_categories["general"])
        return {
            "name": model_name,
            "category": category,
            "emoji": category_info["emoji"],
            "description": category_info["description"]
        }

    def update_models(self):
        """Обновляет список доступных моделей"""
        installed = self.get_installed_models()
        
        if not installed:
            installed = ["qwen2.5vl:7b", "deepseek-r1:7b", "qwen2.5-coder:7b", "llama3.1:latest"]
        
        self.available_models = {}
        for model in installed:
            category = self.categorize_model(model)
            self.available_models[model] = self.get_model_specialization(model, category)
        
        self.last_update = datetime.now()
        return self.available_models

    def estimate_complexity_with_deepseek(self, query, has_image=False):
        """
        DeepSeek оценивает сложность задачи.
        Возвращает число от 0 до 1.
        """
        complexity_prompt = f"""
Ты — анализатор сложности задач. Оцени, насколько сложная задача у пользователя.

ЗАПРОС ПОЛЬЗОВАТЕЛЯ:
{query}

{"(Пользователь прикрепил изображение)" if has_image else ""}

Оцени сложность по шкале от 0 до 1:
- 0.0-0.2: Приветствие, простой вопрос, бытовой разговор
- 0.2-0.4: Короткий вопрос, простой факт, лёгкое объяснение
- 0.4-0.6: Развёрнутый вопрос, анализ, сравнение
- 0.6-0.8: Сложный технический вопрос, код, математика, рассуждения
- 0.8-1.0: Очень сложная задача, глубокий анализ, отладка, многокомпонентный запрос

ОТВЕТЬ ТОЛЬКО ЧИСЛОМ ОТ 0 ДО 1 (например, 0.65).
БЕЗ ПОЯСНЕНИЙ, БЕЗ ТЕКСТА.
"""
        
        response = self.send_to_ollama("deepseek-r1:7b", complexity_prompt)
        
        try:
            match = re.search(r'(\d+\.?\d*)', response)
            if match:
                complexity = float(match.group(1))
                return max(0.0, min(1.0, complexity))
        except:
            pass
        
        return 0.5

    def select_model_by_complexity(self, query, category="general", has_image=False):
        """
        Выбирает модель на основе сложности задачи.
        """
        complexity = self.estimate_complexity_with_deepseek(query, has_image)
        
        # Собираем все модели нужной категории
        models_in_category = []
        for model_name, info in self.available_models.items():
            if info.get("category") == category:
                models_in_category.append((model_name, info))
        
        if not models_in_category:
            # Если нет моделей в категории — берём general
            for model_name, info in self.available_models.items():
                if info.get("category") == "general":
                    models_in_category.append((model_name, info))
        
        if not models_in_category:
            models_in_category = list(self.available_models.items())
        
        if not models_in_category:
            return None, 0.0
        
        # Функция определения размера модели
        def get_size_weight(model_name):
            name_lower = model_name.lower()
            if "70b" in name_lower or "72b" in name_lower:
                return 3.0
            elif "32b" in name_lower or "34b" in name_lower:
                return 2.5
            elif "27b" in name_lower:
                return 2.0
            elif "14b" in name_lower:
                return 1.5
            elif "7b" in name_lower or "8b" in name_lower or "9b" in name_lower:
                return 1.0
            else:
                return 1.0
        
        # Сортируем по размеру (от больших к маленьким)
        models_in_category.sort(key=lambda x: get_size_weight(x[0]), reverse=True)
        
        #ВЫБОР МОДЕЛИ ПО СЛОЖНОСТИ
        if complexity >= 0.7:
            # Сложная задача → самая большая модель
            selected = models_in_category[0][0]
        elif complexity >= 0.4:
            # Средняя задача → средняя модель
            if len(models_in_category) > 1:
                selected = models_in_category[1][0]
            else:
                selected = models_in_category[0][0]
        else:
            # Лёгкая задача → самая маленькая модель
            selected = models_in_category[-1][0]
        
        return selected, complexity

    def analyze_with_deepseek(self, query, has_image=False, custom_models=None):
        """
        ШАГ 1: DeepSeek анализирует запрос, определяет категорию и сложность.
        """
        
        # Обновляем список моделей
        models_to_use = self.available_models or self.update_models()
        
        if not models_to_use:
            models_to_use = {
                "qwen2.5vl:7b": {"category": "vision", "emoji": "📸", "description": "Изображения"},
                "deepseek-r1:7b": {"category": "reasoning", "emoji": "🧠", "description": "Рассуждения"},
                "qwen2.5-coder:7b": {"category": "coding", "emoji": "💻", "description": "Код"},
                "llama3.1:latest": {"category": "general", "emoji": "💬", "description": "Общий"}
            }
        
        #ШАГ 1: ОПРЕДЕЛЯЕМ КАТЕГОРИЮ
        category_prompt = f"""
Определи категорию запроса пользователя.

ЗАПРОС: {query}

ВЫБЕРИ ОДНУ ИЗ КАТЕГОРИЙ:
- coding (программирование, код, алгоритмы)
- reasoning (рассуждения, объяснения, логика)
- math (математика, вычисления)
- vision (изображения, фото) {"(есть изображение)" if has_image else ""}
- general (всё остальное)

ОТВЕТЬ ТОЛЬКО ОДНИМ СЛОВОМ (coding/reasoning/math/vision/general).
БЕЗ ПОЯСНЕНИЙ.
"""
        
        category_response = self.send_to_ollama("deepseek-r1:7b", category_prompt)
        category = "general"
        
        for cat in ["coding", "reasoning", "math", "vision", "general"]:
            if cat in category_response.lower():
                category = cat
                break
        
        # Если есть изображение — всегда vision
        if has_image:
            category = "vision"
        
        #ШАГ 2: ВЫБИРАЕМ МОДЕЛЬ ПО СЛОЖНОСТИ
        selected_model, complexity = self.select_model_by_complexity(query, category, has_image)
        
        if selected_model:
            return {
                "selected_model": selected_model,
                "reason": f"Категория: {category}, сложность: {complexity:.2f}",
                "suggested_prompt": query
            }
        
        # Fallback
        for model, info in models_to_use.items():
            if info.get("category") == "general":
                return {
                    "selected_model": model,
                    "reason": "Fallback: general модель",
                    "suggested_prompt": query
                }
        
        return {
            "selected_model": list(models_to_use.keys())[0],
            "reason": "Fallback: первая доступная модель",
            "suggested_prompt": query
        }

    def send_to_ollama(self, model, prompt, image_path=None, temperature=0.3):
        """Универсальная отправка запроса к Ollama с защитой от зацикливания"""
        
        model_info = self.available_models.get(model, {})
        is_vision = model_info.get("category") == "vision" or "vl" in model.lower() or "vision" in model.lower()
        
        if image_path and not is_vision:
            print(f"⚠️ Модель {model} не поддерживает изображения. Изображение игнорируется.")
            image_path = None
        
        # Сборка полного промпта с историей
        full_prompt = prompt
        
        if self.conversation_history:
            history_text = "\n".join([
                f"{'Пользователь' if m['role'] == 'user' else 'Ассистент'}: {m['content']}"
                for m in self.conversation_history[-5:]
            ])
            full_prompt = f"""
ИСТОРИЯ ДИАЛОГА:
{history_text}

ТЕКУЩИЙ ЗАПРОС:
{prompt}

ОТВЕТЬ НА ТЕКУЩИЙ ЗАПРОС, УЧИТЫВАЯ ИСТОРИЮ ДИАЛОГА.
"""
        
        data = {
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.85,
                "repeat_penalty": 1.2,
                "num_predict": 2048,
                "stop": ["\n\n\n", "---", "###", "=================="]
            }
        }
        
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode("utf-8")
                data["images"] = [image_data]
            except Exception as e:
                return f"❌ Ошибка загрузки изображения: {e}"
        
        try:
            #УВЕЛИЧЕННЫЙ ТАЙМАУТ ДО 600 СЕКУНД (10 МИНУТ)
            response = requests.post(self.ollama_url, json=data, timeout=600)
            if response.status_code == 200:
                return response.json().get("response", "Пустой ответ")
            else:
                error_msg = response.json().get("error", {}).get("message", response.text)
                return f"❌ Ошибка HTTP {response.status_code}: {error_msg}"
        except requests.exceptions.Timeout:
            return "⏱️ Превышено время ожидания (модель слишком долго думает)"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    def clear_history(self):
        """Очищает историю диалога"""
        self.conversation_history = []

    def process(self, query, image_path=None):
        """Полный цикл: DeepSeek анализирует → выбирает → генерирует"""
        start_time = time.time()
        
        self.update_models()
        
        has_image = image_path is not None and os.path.exists(image_path)
        
        analysis = self.analyze_with_deepseek(query, has_image)
        
        model_name = analysis.get("selected_model", "")
        model_info = self.available_models.get(model_name, {})
        
        if not model_info:
            if self.available_models:
                model_name = list(self.available_models.keys())[0]
                model_info = self.available_models[model_name]
            else:
                return {
                    "error": "Нет доступных моделей.",
                    "response": "❌ Нет доступных моделей. Установите модель через `ollama run <имя_модели>`"
                }
        
        model_emoji = model_info.get("emoji", "🤖")
        model_category = model_info.get("category", "general")
        
        optimized_prompt = analysis.get("suggested_prompt", query)
        
        # Дополнительные инструкции для разных категорий
        if model_category == "vision" and image_path:
            optimized_prompt = f"""
{optimized_prompt}

ВАЖНО:
1. Прочитай текст на изображении максимально точно.
2. НЕ ВЫДУМЫВАЙ то, чего нет на картинке.
3. Если текст неразборчив — скажи об этом честно.
4. Ответь КОРОТКО и по делу.
"""
        elif model_category == "coding":
            optimized_prompt = f"""
{optimized_prompt}

ВАЖНО:
1. Покажи пример кода с пояснениями.
2. Если код сложный — разбей на шаги.
3. Не пиши длинные объяснения, только суть.
4. Используй форматирование кода.
"""
        elif model_category == "reasoning":
            optimized_prompt = f"""
{optimized_prompt}

ВАЖНО:
1. Объясни рассуждения пошагово, но КОРОТКО.
2. Если не уверен — скажи "Я не уверен".
3. Не придумывай факты.
"""
        else:
            optimized_prompt = f"""
{optimized_prompt}

ОТВЕТЬ КОРОТКО И ПО ДЕЛУ. МАКСИМУМ 5-7 ПРЕДЛОЖЕНИЙ.
НЕ ПОВТОРЯЙ ОДНО И ТО ЖЕ.
"""
        
        # Сохраняем запрос в историю
        self.conversation_history.append({"role": "user", "content": query})
        
        response = self.send_to_ollama(model_name, optimized_prompt, image_path)
        
        # Сохраняем ответ в историю
        self.conversation_history.append({"role": "assistant", "content": response})
        
        elapsed_time = time.time() - start_time
        
        return {
            "query": query,
            "selected_model": model_name,
            "model_emoji": model_emoji,
            "model_category": model_category,
            "analysis_reason": analysis.get("reason", "Анализ не предоставлен"),
            "response": response,
            "time": elapsed_time
        }


# STREAMLIT ИНТЕРФЕЙС (ТЁМНАЯ ТЕМА)

st.set_page_config(
    page_title="🤖 Smart Chat",
    page_icon="🧠",
    layout="wide"
)

# ===== ТЁМНАЯ ТЕМА =====
st.markdown("""
<style>
    .stApp, body { background-color: #0f1117; color: #e4e4e7; }
    .chat-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .chat-header h1 { margin: 0; font-size: 1.8rem; color: white; }
    .chat-header .status { font-size: 0.9rem; opacity: 0.9; color: white; }
    
    .user-message {
        background: #2a2f3a;
        color: #e4e4e7;
        border-left: 4px solid #667eea;
        padding: 1rem 1.5rem;
        border-radius: 15px 15px 15px 5px;
        margin: 0.5rem 0;
        max-width: 80%;
        float: right;
        clear: both;
    }
    .assistant-message {
        background: #1e2230;
        color: #e4e4e7;
        border-left: 4px solid #22c55e;
        padding: 1rem 1.5rem;
        border-radius: 15px 15px 5px 15px;
        margin: 0.5rem 0;
        max-width: 80%;
        float: left;
        clear: both;
    }
    .model-badge {
        display: inline-block;
        background: #667eea;
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.7rem;
        margin-bottom: 0.5rem;
    }
    
    .stChatInput input {
        background-color: #1a1d23 !important;
        color: #e4e4e7 !important;
        border: 1px solid #3a3f4a !important;
        border-radius: 25px !important;
        padding: 0.75rem 1.5rem !important;
    }
    .stChatInput input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.3) !important;
    }
    
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        font-weight: bold !important;
        padding: 0.5rem 1.5rem !important;
    }
    .stButton button:hover { opacity: 0.9 !important; transform: scale(0.98) !important; }
    
    section[data-testid="stSidebar"] {
        background-color: #1a1d23 !important;
        color: #e4e4e7 !important;
    }
    section[data-testid="stSidebar"] * { color: #e4e4e7 !important; }
    
    .sidebar-info, .model-list {
        background: #0f1117 !important;
        color: #e4e4e7 !important;
        border: 1px solid #2a2f3a !important;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    
    h1, h2, h3, h4, h5, h6 { color: #e4e4e7 !important; }
    p, li, span, div, label { color: #e4e4e7 !important; }
    hr { border-color: #2a2f3a !important; }
    
    ::-webkit-scrollbar { width: 8px; background: #0f1117; }
    ::-webkit-scrollbar-thumb { background: #3a3f4a; border-radius: 10px; }
    
    .footer {
        text-align: center;
        color: #6b7280 !important;
        font-size: 0.8rem;
        padding: 1rem 0;
        margin-top: 2rem;
        border-top: 1px solid #2a2f3a;
    }
</style>
""", unsafe_allow_html=True)

# ИНИЦИАЛИЗАЦИЯ

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "👋 Привет! Я умный диспетчер с **памятью**.\n\n📌 **DeepSeek-R1:7b** анализирует запрос, оценивает сложность и выбирает подходящую модель из ВСЕХ установленных!\n\nПросто напиши сообщение или загрузи фото — я сам выберу лучшую модель и запомню контекст диалога!",
            "model": None
        }
    ]

if "dispatcher" not in st.session_state:
    st.session_state.dispatcher = SmartDispatcher()

if "processed" not in st.session_state:
    st.session_state.processed = False

if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

# ЗАГОЛОВОК

st.markdown("""
<div class="chat-header">
    <div>
        <h1>🧠 Smart Chat</h1>
        <span style="font-size:0.9rem; opacity:0.9;">Адаптивный выбор модели через DeepSeek-R1:7b + ПАМЯТЬ</span>
    </div>
    <div class="status">🟢 Online</div>
</div>
""", unsafe_allow_html=True)

# БОКОВАЯ ПАНЕЛЬ

with st.sidebar:
    st.markdown("### 🎯 Доступные модели")
    
    models = st.session_state.dispatcher.update_models()
    
    if models:
        for model_name, info in models.items():
            st.markdown(f"""
            <div class="model-list">
                {info['emoji']} <b>{model_name}</b><br>
                <span style="font-size:0.8rem; color:#9ca3af;">{info['description']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Модели не найдены.")
    
    st.divider()
    
    if st.button("🔄 Обновить список моделей"):
        st.session_state.dispatcher.update_models()
        st.rerun()
    
    st.divider()
    
    st.markdown("### 🧠 Память")
    st.info(f"Запомнено сообщений: {len(st.session_state.dispatcher.conversation_history)}")
    
    if st.button("🗑️ Очистить историю и память"):
        st.session_state.dispatcher.clear_history()
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "👋 История и память очищены! Начинаем новый диалог.",
                "model": None
            }
        ]
        st.rerun()
    
    st.divider()
    
    st.markdown("### ⚙️ Как это работает")
    st.markdown("""
    1. **DeepSeek-R1:7b** определяет категорию запроса
    2. **DeepSeek-R1:7b** оценивает сложность (0–1)
    3. Выбирается модель под сложность:
       - Лёгкая → маленькая модель (быстро)
       - Сложная → большая модель (качественно)
    
    🔹 Фото → 📸 Vision  
    🔹 Код → 💻 Coder  
    🔹 Вопросы → 🧠 Reasoning  
    🔹 Общение → 💬 General
    """)
    
    st.divider()
    
    st.markdown("### 📸 Загрузить фото")
    uploaded_file = st.file_uploader(
        "Выберите изображение",
        type=["jpg", "jpeg", "png", "gif", "bmp"],
        label_visibility="collapsed",
        key="image_uploader"
    )
    
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        st.image(uploaded_file, caption="📸 Загружено", use_container_width=True)
    
    st.divider()
    st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
    if st.session_state.dispatcher.last_update:
        st.caption(f"📅 Обновлено: {st.session_state.dispatcher.last_update.strftime('%H:%M:%S')}")

# ОТОБРАЖЕНИЕ СООБЩЕНИЙ

chat_container = st.container()

with chat_container:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="user-message">
                <b>👤 Вы</b><br>
                {msg["content"]}
            </div>
            """, unsafe_allow_html=True)
        else:
            model_badge = ""
            if msg.get("model"):
                model_info = st.session_state.dispatcher.available_models.get(
                    msg["model"],
                    {"emoji": "🤖", "description": "Модель"}
                )
                model_badge = f'<span class="model-badge">{model_info["emoji"]} {msg["model"]}</span><br>'
            
            st.markdown(f"""
            <div class="assistant-message">
                {model_badge}
                {msg["content"]}
            </div>
            """, unsafe_allow_html=True)

# ПОЛЕ ВВОДА

st.markdown("---")

user_input = st.chat_input("Напишите сообщение...")

# ОБРАБОТКА ЗАПРОСА

if user_input and not st.session_state.processed:
    st.session_state.processed = True
    
    image_path = None
    if st.session_state.uploaded_file:
        uploaded = st.session_state.uploaded_file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(uploaded.getbuffer())
            image_path = tmp.name
    
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    with st.spinner("🧠 DeepSeek-R1:7b анализирует запрос, оценивает сложность и выбирает модель..."):
        result = st.session_state.dispatcher.process(user_input, image_path)
    
    if "error" in result:
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["error"],
            "model": None
        })
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["response"],
            "model": result["selected_model"]
        })
        
        st.toast(
            f"{result['model_emoji']} Использована: {result['selected_model']} (сложность: {result.get('analysis_reason', 'N/A')})",
            icon="✅"
        )
    
    if image_path and os.path.exists(image_path):
        try:
            os.unlink(image_path)
        except:
            pass
    
    st.session_state.processed = False
    st.rerun()

# ФУТЕР

st.markdown("""
<div class="footer">
    🧠 Smart Dispatcher с памятью • Адаптивный выбор через DeepSeek-R1:7b
</div>
""", unsafe_allow_html=True)