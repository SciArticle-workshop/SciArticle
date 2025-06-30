from rest_framework import serializers

from sciarticle.settings import DOI_REGEX


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


class ValidateBrokenPDFSerializer(serializers.Serializer):
    file = serializers.FileField()
    message_id = serializers.IntegerField()
    chat_id = serializers.IntegerField()
    doi = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=255)
    bot_id = serializers.IntegerField()
