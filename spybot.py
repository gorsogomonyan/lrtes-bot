from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import random
import asyncio

players = {}
spies = []
word = ""
game_started = False

votes = {}
vote_chat = None

words = [
"վանք","դպրոց","բանկ","շուկա","կինոթատրոն","հիվանդանոց","օդանավակայան","կայարան",
"ռեստորան","սրճարան","հյուրանոց","թանգարան","գրադարան","մարզադաշտ","լողավազան","սուպերմարկետ",
"գյուղ","քաղաք","մետրո","կղզի","նավահանգիստ","տուն","բնակարան","գրասենյակ","խոհանոց",
"հյուրասենյակ","լաբորատորիա","բենզալցակայան","ոստիկանություն","բանտ","դատարան",
"խաղահրապարակ","զբոսայգի","լիճ","գետ","լեռ","մթերային խանութ","դեղատուն","հացատուն",
"հյուրատուն","ավտոբուս","գնացք","նավ","ինքնաթիռ","տաքսի","ավտոկայան",
"կրկես","թատրոն","համերգասրահ","սպորտդահլիճ","բասկետբոլի դաշտ","ֆուտբոլի դաշտ",
"դպրոցի բակ","բակ","պարահանդես","ակումբ","դիսկոտեկ","լողափ","անապատ","անտառ",
"ճամբար","կայանատեղի","կամուրջ","ճանապարհ","խաչմերուկ","թունել","տոնավաճառ",
"մոլ","հագուստի խանութ","կոշիկի խանութ","ոսկերչական խանութ","շինանյութի խանութ",
"տպարան","բանկոմատ","համալսարան","դպրոցական դասարան","լսարան","մարզասրահ",
"յոգայի սրահ","սպա կենտրոն","վարսավիրանոց","գեղեցկության սրահ","ֆոտոստուդիա",
"ռադիոկայան","հեռուստաընկերություն","բուսաբանական այգի","կենդանաբանական այգի",
"ակվարիում","ջրաշխարհ","խաղասրահ","բիլիարդ","բոուլինգ","սահադաշտ",
"դահուկային կենտրոն","ռազմաբազա","հրշեջ կայան","շտապ օգնություն"
]

def discussion_time():
    n = len(players)
    if n <= 4:
        return 30
    elif n <= 6:
        return 60
    elif n <= 10:
        return 90
    else:
        return 120

def vote_time():
    n = len(players)
    if n <= 4:
        return 20
    elif n <= 6:
        return 30
    elif n <= 10:
        return 40
    elif n <= 12:
        return 60
    else:
        return 90

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

    await update.message.reply_photo(
        photo=open("logo.jpg","rb"),
        caption="🕵️ SPY GAME\n\nԳրեք /join խաղին միանալու համար\nԱդմինը կսկսի խաղը /start"
    )

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if game_started:
        await update.message.reply_text("Խաղը արդեն սկսվել է")
        return

    user = update.effective_user

    if user.id in players:
        return

    players[user.id] = user.first_name

    text = "👥 Խաղացողներ\n\n"

    i = 1
    for p in players:
        text += f"{i}. {players[p]}\n"
        i += 1

    await update.message.reply_text(text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global spies, word, game_started, vote_chat

    if not await is_admin(update, context):
        return

    if len(players) < 4:
        await update.message.reply_text("Պետք է առնվազն 4 խաղացող")
        return

    game_started = True

    vote_chat = update.effective_chat.id

    word = random.choice(words)

    ids = list(players.keys())

    spy_count = max(1, len(ids)//4)

    spies = random.sample(ids, spy_count)

    for p in ids:

        if p in spies:
            await context.bot.send_message(p,"🤫 Դու Լրտես ես")
        else:
            await context.bot.send_message(p,f"📍 Բառը — {word}")

    t = discussion_time()

    await update.message.reply_text(f"💬 Քննարկում {t} վայրկյան")

    await asyncio.sleep(t)

    await vote(update, context)

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global votes

    votes = {}

    keyboard = []

    for p in players:
        keyboard.append(
            [InlineKeyboardButton(players[p], callback_data=str(p))]
        )

    keyboard.append(
        [InlineKeyboardButton("❓ Կասկած չկա", callback_data="skip")]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        vote_chat,
        "🗳 Ընտրեք ում եք կասկածում",
        reply_markup=reply_markup
    )

    t = vote_time()

    asyncio.create_task(vote_timer(context,t))

async def vote_timer(context,t):

    await asyncio.sleep(t)

    if game_started and len(votes) < len(players):
        await finish_vote(context)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global votes

    query = update.callback_query
    await query.answer()

    voter = query.from_user.id
    voted = query.data

    if voter in votes:
        return

    votes[voter] = voted

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
            "🤷 Կասկած չկա\nՔննարկումը շարունակվում է"
        )

        t = discussion_time()

        await asyncio.sleep(t)

        await vote(None,context)

        return

    voted = max(counts, key=counts.get)

    if voted in spies:

        spy_names=[]
        citizen_names=[]

        for p in players:

            if p in spies:
                spy_names.append(players[p])
            else:
                citizen_names.append(players[p])

        await context.bot.send_message(
            vote_chat,
            "🎉 Խաղը ավարտվեց\n\n"
            f"📍 Ճիշտ բառը — {word}\n\n"
            "🏆 Հաղթողներ\n"+"\n".join(citizen_names)+
            "\n\n❌ Պարտվողներ\n"+"\n".join(spy_names)
        )

        game_started=False

    else:

        await context.bot.send_message(
            vote_chat,
            f"❌ {players[voted]} լրտես չէր\nՔննարկումը շարունակվում է"
        )

        t=discussion_time()

        await asyncio.sleep(t)

        await vote(None,context)

app = ApplicationBuilder().token("7950712985:AAFQTLOVMb3Jwk19HZzs85Fs78MvolHpocI").build()

app.add_handler(CommandHandler("lrtes", lrtes))
app.add_handler(CommandHandler("join", join))
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

app.run_polling()
