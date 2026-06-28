import os
import anthropic
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# Настройки
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Настройка Claude
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Этапы онбординга
ASK_NAME, ASK_AGE, ASK_SKIN_TYPE, ASK_SKIN_CONCERNS = range(4)

# Список запрещённых ингредиентов
BANNED_INGREDIENTS = """
ЗАПРЕЩЁННЫЕ И ОГРАНИЧЕННЫЕ ИНГРЕДИЕНТЫ (ЕС №1223/2009 и ТР ТС 009/2011):

СНИЖАЮТ ОЦЕНКУ НА 25+ БАЛЛОВ:
- Формальдегид и его доноры (DMDM Hydantoin, Imidazolidinyl Urea, Diazolidinyl Urea, Quaternium-15, Bronopol)
- Парабены (Propylparaben, Butylparaben, Isopropylparaben, Isobutylparaben)
- Фталаты (Dibutyl Phthalate, Diethyl Phthalate)
- Триклозан (Triclosan)
- Гидрохинон (Hydroquinone)
- Ртутьсодержащие соединения
- Свинец и его соединения

СНИЖАЮТ ОЦЕНКУ НА 10-20 БАЛЛОВ:
- BHA (Butylated Hydroxyanisole) в высоких концентрациях
- Этиловый спирт в первых 3 позициях состава
- SLS/SLES в средствах без смывания
- Синтетические отдушки (Fragrance/Parfum) для чувствительной кожи
- Минеральное масло как основа
- Oxybenzone (эндокринный риск)
- Octinoxate/Ethylhexyl Methoxycinnamate (эндокринный риск)

ТРЕБУЮТ ВНИМАНИЯ:
- Methylisothiazolinone (MI) — частый аллерген
- Methylchloroisothiazolinone (MCI) — частый аллерген
- Propylene Glycol в высоких концентрациях
- Artificial colorants (CI номера)
"""

PROMPT_TEMPLATE = """Ты эксперт по косметической безопасности с глубоким знанием европейского регламента ЕС №1223/2009 и российского техрегламента ТР ТС 009/2011.

Пользователь: {name}, {age} лет.
Тип кожи: {skin_type}
Особенности кожи: {skin_concerns}

Пользователь хочет узнать про косметическое средство: {product}

{banned_ingredients}

Найди полный INCI-состав этого средства по своим знаниям. Оцени каждый ингредиент по 4 критериям:
1. Риск аллергии
2. Эндокринный риск
3. Канцерогенность
4. Риск при высокой концентрации

СТРОГИЕ ПРАВИЛА ОЦЕНКИ:
— Ингредиенты в начале состава = высокая концентрация = больший вес
— Запрещённые ингредиенты из списка выше → снижай оценку согласно правилам
— Только безопасные ингредиенты → минимум 80 баллов
— 1-2 спорных ингредиента → 50-75 баллов
— Несколько проблемных → 25-50 баллов
— Запрещённые ингредиенты → максимум 45 баллов

Ответ СТРОГО по формату (не более 400 слов):

🔍 Средство: [название]

📋 Состав: [полный INCI список]

⚠️ Требуют внимания:
— [Ингредиент]: [риск и причина] — [Low/Moderate/High risk]
(если всё чисто → "не обнаружено ✓")

✅ Оценка безопасности: [число]/100 — [Excellent/Good/Not great/Bad]
Excellent: 76-100 | Good: 51-75 | Not great: 26-50 | Bad: 0-25

👤 Совместимость с твоей кожей:
— Подходит: [да/частично/нет] — [краткое объяснение]
— Особое внимание: [ингредиенты актуальные для {skin_type} кожи и {skin_concerns}]

💬 Вывод для {name}: [2-3 персональных предложения]"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("profile_complete"):
        name = context.user_data.get("name", "")
        await update.message.reply_text(
            f"👋 С возвращением, {name}!\n\n"
            "Напиши название косметического средства для анализа.\n\n"
            "Чтобы обновить профиль — напиши /reset"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "👋 Привет! Я бот *Ингредиент* — анализирую составы косметики.\n\n"
        "Задам тебе несколько вопросов для персональных рекомендаций.\n\n"
        "Как тебя зовут?",
        parse_mode="Markdown"
    )
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        f"Приятно познакомиться, {context.user_data['name']}! 😊\n\nСколько тебе лет?"
    )
    return ASK_AGE


async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    age_text = update.message.text.strip()
    if not age_text.isdigit():
        await update.message.reply_text("Пожалуйста, введи возраст цифрами (например: 25)")
        return ASK_AGE
    context.user_data["age"] = age_text
    keyboard = [["Нормальная", "Сухая"], ["Жирная", "Комбинированная"], ["Чувствительная"]]
    await update.message.reply_text(
        "Какой у тебя тип кожи?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_SKIN_TYPE


async def ask_skin_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["skin_type"] = update.message.text.strip()
    keyboard = [
        ["Акне и постакне", "Пигментация"],
        ["Морщины", "Купероз"],
        ["Обезвоженность", "Расширенные поры"],
        ["Нет особенностей"]
    ]
    await update.message.reply_text(
        "Есть ли особенности кожи?\n(выбери из списка или напиши своё)",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_SKIN_CONCERNS


async def ask_skin_concerns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["skin_concerns"] = update.message.text.strip()
    context.user_data["profile_complete"] = True
    name = context.user_data["name"]
    skin_type = context.user_data["skin_type"]
    skin_concerns = context.user_data["skin_concerns"]
    await update.message.reply_text(
        f"✅ Профиль создан!\n\n"
        f"👤 {name}\n"
        f"🧴 Тип кожи: {skin_type}\n"
        f"💡 Особенности: {skin_concerns}\n\n"
        f"Теперь напиши название любого косметического средства — дам персональный анализ!",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("profile_complete"):
        await update.message.reply_text(
            f"👤 Твой профиль:\n\n"
            f"Имя: {context.user_data.get('name', '')}\n"
            f"Возраст: {context.user_data.get('age', '')}\n"
            f"Тип кожи: {context.user_data.get('skin_type', '')}\n"
            f"Особенности: {context.user_data.get('skin_concerns', '')}\n\n"
            f"Чтобы обновить — напиши /reset"
        )
    else:
        await update.message.reply_text("Профиль не создан. Напиши /start!")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Профиль сброшен. Напиши /start чтобы создать новый!")


async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("profile_complete"):
        await update.message.reply_text("Сначала создай профиль — напиши /start!")
        return

    product = update.message.text.strip()
    name = context.user_data.get("name", "пользователь")
    age = context.user_data.get("age", "не указан")
    skin_type = context.user_data.get("skin_type", "не указан")
    skin_concerns = context.user_data.get("skin_concerns", "не указаны")

    loading_msg = await update.message.reply_text(
        f"🔍 Анализирую состав для тебя, {name}...\nЭто займёт несколько секунд ⏳"
    )

    try:
        prompt = PROMPT_TEMPLATE.format(
            name=name, age=age, skin_type=skin_type,
            skin_concerns=skin_concerns, product=product,
            banned_ingredients=BANNED_INGREDIENTS
        )

        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        result = message.content[0].text
        if len(result) > 4000:
            result = result[:4000] + "...\n\n_(ответ сокращён)_"

        await loading_msg.delete()
        await update.message.reply_text(result)

    except Exception as e:
        await loading_msg.delete()
        await update.message.reply_text("😔 Произошла ошибка при анализе. Попробуй ещё раз!")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено. Напиши /start чтобы начать заново!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            ASK_SKIN_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_skin_type)],
            ASK_SKIN_CONCERNS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_skin_concerns)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze))
    print("Бот Ингредиент запущен на Claude! 🚀")
    app.run_polling()


if __name__ == "__main__":
    main()
