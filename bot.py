import os
import re
import json
import logging
import asyncio
from openai import OpenAI
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = (
    "Sos un asistente pedagógico para estudiantes de Agronomía. "
    "Clasificá un escrito como 'descriptiva', 'argumentativa', 'mixta' o 'indefinida'. "
    "RESPONDE SOLO en JSON con este formato:\n"
    "{\n"
    '  "tipo": "descriptiva|argumentativa|mixta|indefinida",\n'
    '  "explicacion": "breve explicación",\n'
    '  "sugerencias": "acciones para mejorar",\n'
    '  "fragmentos_descriptivos": ["..."],\n'
    '  "fragmentos_argumentativos": ["..."]\n'
    "}"
)

def clasificar_con_ia(texto: str):
    prompt = f'Texto del alumno:\n"""{texto}"""'
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": prompt}],
        temperature=0
    )
    return resp.choices[0].message.content

def extraer_json(texto: str):
    try:
        match = re.search(r"\{.*\}", texto, flags=re.DOTALL)
        if not match: return None
        return json.loads(match.group(0))
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [["🔄 Reiniciar", "📖 Ver ejemplo"], ["❓ Ayuda"]]
    reply = ReplyKeyboardMarkup(teclado, resize_keyboard=True)
    await update.message.reply_text("👋 Hola, enviame un texto y lo analizaré.", reply_markup=reply)

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Escribí un párrafo y te diré si es descriptivo o argumentativo.")

async def ejemplo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 Descriptivo: 'El maíz tiene hojas anchas y tallos resistentes.'\n\n"
        "📗 Argumentativo: 'El maíz transgénico debería usarse porque aumenta la resiliencia.'"
    )

async def analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if texto in ["❓ Ayuda"]: return await ayuda(update, context)
    if texto in ["📖 Ver ejemplo"]: return await ejemplo(update, context)
    if texto in ["🔄 Reiniciar"]: return await start(update, context)

    msg = await update.message.reply_text("🔎 Analizando tu texto con IA...")
    try:
        raw = await asyncio.to_thread(clasificar_con_ia, texto)
        data = extraer_json(raw) or {"tipo": "indefinida", "explicacion": "Error de análisis", "sugerencias": "", "fragmentos_descriptivos": [], "fragmentos_argumentativos": []}
        respuesta = f"📊 Tipo: {data['tipo']}\n\n🔍 Explicación: {data['explicacion']}\n\n💡 Sugerencias: {data['sugerencias']}"
        await msg.edit_text(respuesta)
    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {e}")

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token: raise ValueError("Falta TELEGRAM_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("ejemplo", ejemplo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analizar))
    print("🤖 Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
