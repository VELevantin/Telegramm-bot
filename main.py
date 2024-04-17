import logging
import random
from config import BOT_TOKEN
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from tasks import beginner_tasks, intermediate_tasks, advanced_tasks, native_speaker_tasks


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

CHOOSING_LEVEL, CHOOSING_TASK, DOING_TASK, CHOOSING_ACTION = range(4)

reply_keyboard_level = [
    ["Новичок", "Средний", "Высокий", "Носитель"],
]
markup_level = ReplyKeyboardMarkup(reply_keyboard_level, one_time_keyboard=True, resize_keyboard=True)

reply_keyboard_task = [
    ["Перевести текст", "Перевести слово", "Дополнить перевод", "Получить очки"],
]
markup_task = ReplyKeyboardMarkup(reply_keyboard_task, one_time_keyboard=True, resize_keyboard=True)

reply_keyboard_action = [
    ["Продолжить", "Сменить уровень", "Сменить тип задания"],
]
markup_action = ReplyKeyboardMarkup(reply_keyboard_action, one_time_keyboard=True, resize_keyboard=True)


user_scores = {}

user_data = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Привет! Я бот для изучения английского языка. "
        "Какой у тебя уровень владения английским языком?",
        reply_markup=markup_level,
    )

    return CHOOSING_LEVEL


async def choose_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    context.user_data["level"] = text.lower()
    await update.message.reply_text(
        f"Отлично! Ты выбрал уровень {text.lower()}. "
        "Давай порешаем немного заданий, за каждое задание ты будешь получать очки (пока что они бесполезные). "
        "С какого типа заданий хочешь начать?",
        reply_markup=markup_task,
    )

    return CHOOSING_TASK


async def generate_task(level: str, task_type: str) -> str:
    task = ""
    if level.lower() == "новичок":
        tasks = beginner_tasks.get(task_type)
    elif level.lower() == "средний":
        tasks = intermediate_tasks.get(task_type)
    elif level.lower() == "высокий":
        tasks = advanced_tasks.get(task_type)
    elif level.lower() == "носитель":
        tasks = native_speaker_tasks.get(task_type)
    if tasks:
        task = random.choice(tasks)
    return task


async def choose_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    level = context.user_data.get("level")
    if text == "Получить очки":
        await update.message.reply_text("К сожалению, сейчас получить очки другим способом нельзя.")
        return DOING_TASK
    else:
        task = await generate_task(level, text)
        if task:
            await update.message.reply_text(f"Ты выбрал задание {text}. Мы начинаем!")
            if text == "Перевести слово":
                await update.message.reply_text(f"Переведи слово: *{task}*", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"Задание: {task}")
            context.user_data["task"] = task
            context.user_data["task_type"] = text
            return DOING_TASK
        else:
            await update.message.reply_text("К сожалению, для данного уровня и типа задания задание не найдено.")
    return ConversationHandler.END


async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_answer = update.message.text
    task = context.user_data.get("task")
    is_correct = random.choice([True, False])
    new_score = 0

    if is_correct:
        current_score = user_scores.get(update.effective_user.id, 0)

        if context.user_data["level"] == "новичок":
            new_score = current_score + 1

        elif context.user_data["level"] == "средний":
            new_score = current_score + 2

        elif context.user_data["level"] == "высокий":
            new_score = current_score + 3

        elif context.user_data["level"] == "носитель":
            new_score = current_score + 4

        user_scores[update.effective_user.id] = new_score

        await update.message.reply_text("Правильно! Твой счет теперь: {}".format(new_score))
        await update.message.reply_text("Что ты хочешь сделать дальше?", reply_markup=markup_action)

        return CHOOSING_ACTION

    else:
        await update.message.reply_text("Неправильно. Попробуй еще раз.")
        await update.message.reply_text(f"Задание: {task}")

        return DOING_TASK


async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    level = context.user_data.get("level")
    task = context.user_data.get("task")
    task_type = context.user_data.get("task_type")

    if text == "Продолжить":
        task = await generate_task(level, task_type)
        if task:
            if text == "Перевести слово":
                await update.message.reply_text(f"Переведи слово: *{task}*", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"Задание: {task}")
            context.user_data["task"] = task
            return DOING_TASK
        else:
            await update.message.reply_text("К сожалению, для данного уровня и типа задания задание не найдено.")
            return ConversationHandler.END
    elif text == "Сменить уровень":
        await update.message.reply_text("Какой уровень ты хочешь выбрать?", reply_markup=markup_level)
        return CHOOSING_LEVEL
    elif text == "Сменить тип задания":
        await update.message.reply_text("Какой тип задания ты хочешь выбрать?", reply_markup=markup_task)
        return CHOOSING_TASK

    return DOING_TASK


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_LEVEL: [
                MessageHandler(
                    filters.Regex("^(Новичок|Средний|Высокий|Носитель)$"), choose_level
                ),
            ],
            CHOOSING_TASK: [
                MessageHandler(
                    filters.Regex("^(Перевести текст|Перевести слово|Дополнить перевод|Получить очки)$"), choose_task
                ),
            ],
            DOING_TASK: [
                MessageHandler(filters.TEXT, check_answer),
            ],
            CHOOSING_ACTION: [
                MessageHandler(filters.Regex("^(Продолжить🫡|Сменить уровень|Сменить тип задания)$"), choose_action),
            ],
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

