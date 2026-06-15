import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройки
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

PROMPT_TEMPLATE = """Ты эксперт по косметической безопасности. Пользователь назвал косметическое средство: {product}.

Найди его состав по своим знаниям и оцени безопасность. Ответ строго по формату и не более 200 слов:

🔍 Средство: [название]

📋 Состав: [5-7 главных ингредиентов]

⚠️ Опасные компоненты: [список или "не обнаружено"]

✅ Оценка безопасности: [число]/100

💬 Вывод: [1-2 предложения]"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот-анализатор косметики *Ингредиент*.\n\n"
        "Напиши название любого косметического средства, и я:\n"
        "• Найду его состав\n"
        "• Выявлю опасные компоненты\n"
        "• Дам оценку безопасности от 0 до 100\n\n"
        "Попробуй написать, например: _Cerave Moisturizing Cream_",
        parse_mode="Markdown"
    )

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product = update.message.text
    
    # Сообщение о загрузке
    loading_msg = await update.message.reply_text("🔍 Анализирую состав, подождите немного...")
    
    try:
        response = model.generate_content(PROMPT_TEMPLATE.format(product=product))
        result = response.text
        
        await loading_msg.delete()
        await update.message.reply_text(result)
        
    except Exception as e:
        await loading_msg.delete()
        await update.message.reply_text("😔 Произошла ошибка при анализе. Попробуйте ещё раз через минуту.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze))
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
