from django.db import models


class Translation(models.Model):
    key = models.ForeignKey(
        "TranslateKey",
        related_name="translations",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="All translations for the key."
    )
    language = models.ForeignKey(
        "Language",
        on_delete=models.CASCADE,
        related_name="translations",
        null=True,
        blank=True,
        help_text="All translations for the key."
    )
    text = models.TextField(
        help_text="Translations."
    )

    @classmethod
    def create_from_list(cls, language, pairs):
        """

        :param language: Language
        :param pairs: list((id of TranslateKey, text), ...)
        :return: list of Translation
        """
        exists = set(
            cls.objects
            .filter(language=language, key_id__in=[i[0] for i in pairs])
            .values_list("key_id", flat=True)
        )

        data_to_create = [cls(language=language, key_id=i[0], text=i[0])
                          for i in pairs if i[0] not in exists]

        return cls.objects.bulk_create(data_to_create)

    def __str__(self):
        return f"{self.key.key}: {self.language}"

    class Meta:
        unique_together = ("key", "language")
