import asyncio
import logging
import sys
from aiogram import Bot
from backend.app.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_connection():
    settings = get_settings()
    
    token = settings.TELEGRAM_BOT_TOKEN
    chat_ids = settings.TELEGRAM_ALLOWED_CHAT_IDS
    
    if not token:
        print("❌ ERRO: TELEGRAM_BOT_TOKEN não configurado no .env")
        return
    if not chat_ids:
        print("❌ ERRO: TELEGRAM_ALLOWED_CHAT_IDS não configurado no .env")
        return

    target_chat_id = chat_ids[0]
    print(f"Tentando enviar mensagem para o chat {target_chat_id}...")

    bot = Bot(token=token)
    try:
        await bot.send_message(
            chat_id=target_chat_id,
            text="🚀 **AI Trend Creator: Teste de Conexão**\n\nO bot está configurado corretamente e consegue te enviar mensagens! ✅"
        )
        print("✅ SUCESSO: Mensagem enviada com êxito!")
    except Exception as e:
        print(f"❌ FALHA: Não foi possível enviar a mensagem.\nErro: {e}")
        print("\nLembre-se: Você PRECISA enviar /start para o bot no Telegram antes de testar.")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
