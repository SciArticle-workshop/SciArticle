import logging

from asgiref.sync import async_to_sync
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from bot.tasks import request_pdf_task, validate_broken_pdf
from bot.models import Request
from .serializers import (
    RequestSerializer,
    RequestUpdateSerializer,
    ValidateBrokenPDFSerializer
)

logger = logging.getLogger(__name__)
validate_broken_pdf_sync = async_to_sync(validate_broken_pdf)


class RequestAPIView(APIView):
    """Получение Post-запроса для request_pdf."""

    def post(self, request):
        serializer = RequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        chat_id = serializer.validated_data['chat_id']
        message_id = serializer.validated_data['message_id']
        doi = serializer.validated_data['doi']
        message_search_id = serializer.validated_data['message_search_id']

        logger.info(
            f"Request received: for article doi:{doi} from chat_id:{chat_id}")

        result, _ = request_pdf_task(
            chat_id,
            message_id,
            doi,
            f'user_{chat_id}',
            message_search_id,
        )
        if not result:
            return Response(status=status.HTTP_409_CONFLICT)
        return Response(result, status.HTTP_201_CREATED)

    def put(self, request, pk):
        logger.info(f"Request received: for request id={pk}")

        req = Request.objects.get(pk=pk)
        serializer = RequestUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        message_search_id = serializer.validated_data['message_search_id']
        req.message_search_id = message_search_id
        req.save()

        return Response(status=status.HTTP_200_OK)


class ValidateBrokenPDFView(APIView):
    """
    Получение post-запроса о сломанном pdf.
    Создание запроса в бд.
    Отправка файла в общий чат для дополнительной проверки.
    """

    def post(self, request):
        serializer = ValidateBrokenPDFSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data['file']
        doi = serializer.validated_data['doi']
        username = serializer.validated_data['username']
        chat_id = serializer.validated_data['chat_id']
        message_id = serializer.validated_data['message_id']
        bot_id = serializer.validated_data['bot_id']

        logger.info(
            f"Request received: for article doi:{doi} from chat_id:{chat_id}. Broken PDF"
        )
        result, pdf_request = request_pdf_task(chat_id, message_id, doi,
                                               username, 0)
        if not result:
            return Response(status=status.HTTP_409_CONFLICT)
        if result['code'] == 'repeated request':
            logger.info(f"Repeat request: {result}")
            return Response(result, status.HTTP_200_OK)
        validate_broken_pdf_sync(file, doi, pdf_request, bot_id)

        return Response(result, status.HTTP_200_OK)
