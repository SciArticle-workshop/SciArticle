from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import RequestSerializer
from bot.tasks import request_pdf_task

import logging

logger = logging.getLogger(__name__)


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
                f"Request received: for article doi={doi} from chat_id={chat_id}"
            )

            request_pdf_task(chat_id, message_id, doi, message_search_id)
            return Response(status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
