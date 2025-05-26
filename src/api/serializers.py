import re

from rest_framework import serializers


DOI_REGEX = re.compile(r'^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$')


class RequestSerializer(serializers.Serializer):
    chat_id = serializers.IntegerField()
    message_id = serializers.IntegerField()
    doi = serializers.CharField(max_length=256)
    message_search_id = serializers.IntegerField()

    def validate_doi(self, value):
        """
        Проверяет формат DOI.
        """
        if not DOI_REGEX.match(value):
            raise serializers.ValidationError("Invalid format DOI")
        return value

class RequestUpdateSerializer(serializers.Serializer):
    message_search_id = serializers.IntegerField()
