import os

from asgiref.sync import async_to_sync
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from .serializers import (
    RequestSerializer,
    RequestUpdateSerializer,
    ValidateBrokenPDFSerializer
)

from bot.tasks import request_pdf_task, validate_broken_pdf
from bot.models import Request


import logging

PDF_FILE = './pdf_files'
os.makedirs(PDF_FILE, exist_ok=True)

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is not set in environment variables")
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

validate_broken_pdf_sync = async_to_sync(validate_broken_pdf)

class RequestAPIView(APIView):
    """Получение Post-запроса для request_pdf"""

    def post(self, request):
        serializer = RequestSerializer(data=request.data)
        if serializer.is_valid():
            chat_id = serializer.validated_data['chat_id']
            message_id = serializer.validated_data['message_id']
            doi = serializer.validated_data['doi']
            message_search_id = serializer.validated_data['message_search_id']

            logger.info(
                f"Request received: for article doi:{doi} from chat_id:{chat_id}"
            )

            result, pdf_request = request_pdf_task(
                chat_id,
                message_id,
                doi,
                f'user_{chat_id}',
                message_search_id,
            )
            if not result:
                return Response(status=status.HTTP_409_CONFLICT)
            return Response(result, status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        logger.info(
            f"Request received: for request id={pk}"
        )

        req = Request.objects.get(pk=pk)
        serializer = RequestUpdateSerializer(data=request.data)
        if serializer.is_valid():
            message_search_id = serializer.validated_data['message_search_id']

            req.message_search_id = message_search_id
            req.save()

            return Response(status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ValidateBrokenPDFView(APIView):
    """
    Получение post-запроса о сломанном pdf.
    Создание запроса в бд.
    Отправка файла в общий чат для дополнительной проверки.
    """

    def post(self, request):
        serializer = ValidateBrokenPDFSerializer(data=request.data)
        logger.info('Запрос получен')
        if serializer.is_valid():
            file = serializer.validated_data['file']
            doi = serializer.validated_data['doi']
            username = serializer.validated_data['username']
            chat_id = serializer.validated_data['chat_id']
            message_id = serializer.validated_data['message_id']
            bot_id = serializer.validated_data['bot_id']

            logger.info(
                f"Request received: for article doi:{doi} from chat_id:{chat_id}. Broken PDF."
            )
            result, pdf_request = request_pdf_task(
                chat_id,
                message_id,
                doi,
                username,
                0
            )
            if not result:
                return Response(status=status.HTTP_409_CONFLICT)

            validate_broken_pdf_sync(file, doi, pdf_request, bot_id)
            return Response(result, status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
