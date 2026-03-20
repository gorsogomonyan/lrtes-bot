from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import random
import asyncio
import os
TOKEN = os.getenv("BOT_TOKEN")

players = {}
spies = []
word = ""
game_started = False

votes = {}
vote_chat = None

words = [
"վանք","դպրոց","բանկ","շուկա","կինոթատրոն",
"հիվանդանոց","օդանավակայան","կայարան",
"ռեստորան","սրճարան","հյուրանոց",
"թանգարան","գրադարան","մարզադաշտ",
"լողավազան","սուպերմարկետ"
]

def discussion_time():

    n = len(players)

    if n <= 5:
        return 60
    elif n <= 8:
        return 90
    elif n <= 12:
        return 120
    else:
        return 240


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )

    return member.status in ["administrator","creator"]


async def lrtes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global players, game_started

    if not await is_admin(update, context):
        await update.message.reply_text("⛔ Միայն ադմինը կարող է բացել խաղը")
        return

    players = {}
    game_started = False

    await update.message.reply_text(
        "🕵️ Լրտես խաղը բացվեց\n\n"
        "Գրեք /join խաղին միանալու համար\n"
        "Ադմինը կսկսի խաղը /start"
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if game_started:
        await update.message.reply_text("Խաղը արդեն սկսվել է")
        return

    user = update.effective_user
    players[user.id] = user.first_name

    text = "👥 Խաղացողներ\n\n"

    i = 1
    for p in players:
        text += f"{i}. {players[p]}\n"
        i += 1

    await update.message.reply_text(text)


async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id in players:

        name = players[user.id]
        del players[user.id]

        await update.message.reply_text(f"{name} դուրս եկավ խաղից")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global spies, word, game_started

    if not await is_admin(update, context):
        await update.message.reply_text("⛔ Միայն ադմինը կարող է սկսել խաղը")
        return

    if len(players) < 4:
        await update.message.reply_text("Պետք է առնվազն 4 խաղացող")
        return

    game_started = True

    word = random.choice(words)

    ids = list(players.keys())

    spy_count = max(1, len(ids)//4)

    spies = random.sample(ids, spy_count)

    for p in ids:

        if p in spies:
            await context.bot.send_message(p,"🤫 Դու Լրտես ես")
        else:
            await context.bot.send_message(p,f"📍 Բառը՝ {word}")

    t = discussion_time()

    await update.message.reply_text(
        f"💬 Քննարկում\nԺամանակը՝ {t//60} րոպե"
    )

    await asyncio.sleep(t)

    await update.message.reply_text("🗳 Գրեք /vote")


async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global votes, vote_chat

    votes = {}
    vote_chat = update.effective_chat.id

    keyboard = []

    for p in players:
        keyboard.append(
            [InlineKeyboardButton(players[p], callback_data=str(p))]
        )

    keyboard.append(
        [InlineKeyboardButton("❓ Կասկած չկա", callback_data="skip")]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🗳 Ընտրեք ում եք կասկածում",
        reply_markup=reply_markup
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global votes

    query = update.callback_query
    await query.answer()

    voter = query.from_user.id
    voted = query.data

    if voter in votes:
        return

    votes[voter] = voted

    voter_name = query.from_user.first_name

    if voted == "skip":

        await context.bot.send_message(
            vote_chat,
            f"🤷 {voter_name} ասաց «Կասկած չկա»"
        )

    else:

        voted = int(voted)

        await context.bot.send_message(
            vote_chat,
            f"🗳 {voter_name} ընտրեց {players[voted]}"
        )

    await query.edit_message_reply_markup(None)

    if len(votes) == len(players):
        await finish_vote(context)


async def finish_vote(context):

    global game_started

    counts = {}

    for v in votes.values():

        if v == "skip":
            continue

        v = int(v)

        counts[v] = counts.get(v,0)+1

    if not counts:

        await context.bot.send_message(
            vote_chat,
            "🤷 Կասկած չկա\nՆոր քննարկում"
        )

        t = discussion_time()

        await asyncio.sleep(t)

        await context.bot.send_message(
            vote_chat,
            "Գրեք /vote"
        )

        return

    voted = max(counts, key=counts.get)

    if voted in spies:

        await context.bot.send_message(
            vote_chat,
            f"🎉 Հաղթեցիք!\n\n{players[voted]} լրտես էր"
        )

        game_started = False

    else:

        await context.bot.send_message(
            vote_chat,
            f"❌ {players[voted]} լրտես չէր"
        )


async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global game_started

    user = update.effective_user

    if user.id not in spies:
        await update.message.reply_text("Միայն լրտեսը կարող է գուշակել")
        return

    guess_word = " ".join(context.args)

    if guess_word.lower() == word.lower():

        await update.message.reply_text(
            "🕵️ Լրտեսը հաղթեց!\nԽաղը ավարտվեց"
        )

        game_started = False

    else:

        await update.message.reply_text("❌ Սխալ բառ")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global players, spies, game_started

    if not await is_admin(update, context):
        await update.message.reply_text("⛔ Միայն ադմինը կարող է չեղարկել խաղը")
        return

    players = {}
    spies = []
    game_started = False

    await update.message.reply_text("Խաղը չեղարկվեց")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("lrtes", lrtes))
app.add_handler(CommandHandler("join", join))
app.add_handler(CommandHandler("leave", leave))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("vote", vote))
app.add_handler(CommandHandler("guess", guess))
app.add_handler(CommandHandler("cancel", cancel))
app.add_handler(CallbackQueryHandler(button))

app.run_polling()
