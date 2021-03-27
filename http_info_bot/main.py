import logging
import unicodedata
from dataclasses import dataclass
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from emoji import emojize
from telegram import ParseMode, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

from config import settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


@dataclass
class HttpInfo:
    title: str
    description: str


class MDNRequestException(Exception):
    def __init__(self, message="Houve uma falha na comunicação com o MDN"):
        self.message = message
        super().__init__(self.message)


class HTTPCatRequestException(Exception):
    def __init__(self, message="Houve uma falha na comunicação com o http.cat"):
        self.message = message
        super().__init__(self.message)


class HTTPCodeRequiredException(Exception):
    def __init__(self, message="O código HTTP deve ser informado"):
        self.message = message
        super().__init__(self.message)


def get_info_http_code_mdn(code) -> HttpInfo:
    response = requests.get(
        f"https://developer.mozilla.org/pt-BR/docs/Web/HTTP/Status/{code}"
    )

    if response.ok:
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.h1.text
        unicode_str = soup.find("meta", attrs={"name": "description"}).get("content")
        description = unicodedata.normalize("NFKD", unicode_str)
        return HttpInfo(title, description)
    else:
        raise MDNRequestException()


def get_cat_image_http_code(code) -> BytesIO:
    response = requests.get(f"https://http.cat/{code}.jpg")
    if response.ok:
        image_bytes = BytesIO(response.content)
        return image_bytes
    else:
        raise HTTPCatRequestException()


def hello(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"Olá, {update.effective_user.first_name}")


def unknown(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Desculpe, não conheço esse comando."
    )


def http_info(update: Update, context: CallbackContext):
    try:
        payload = context.args
        code = payload[0] if len(payload) else None

        if not code:
            raise HTTPCodeRequiredException()

        info = get_info_http_code_mdn(code)
        photo = get_cat_image_http_code(code)
        caption = (
            f"*{info.title}*\n\n"
            f"{info.description}\n\n"
            f"Fonte: [MDN](https://developer.mozilla.org/) {emojize(':heart:', use_aliases=True)}\n"
            f"Imagem: [http.cat](https://http.cat/) {emojize(':heart_eyes_cat:', use_aliases=True)}"
        )

        context.bot.send_photo(
            chat_id=update.effective_message.chat_id,
            photo=photo,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
        )
    except HTTPCodeRequiredException as ex:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(f"{ex.message}\n\n" f"Exemplo:\n" f"`/http 200`"),
            parse_mode=ParseMode.MARKDOWN,
        )
    except (MDNRequestException, HTTPCatRequestException) as ex:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"Desculpe, não foi possível processar a sua solicitação.\n\n"
                f"Detalhes:\n"
                f"`{ex.message}`"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )


if __name__ == "__main__":
    updater = Updater(settings.telegram_token)

    updater.dispatcher.add_handler(CommandHandler("hello", hello))
    updater.dispatcher.add_handler(CommandHandler("http", http_info, pass_args=True))
    updater.dispatcher.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()
    updater.idle()
