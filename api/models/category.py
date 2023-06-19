from django.db import models


class Category(models.Model):
    name = models.CharField(
        max_length=128,
        blank=False,
        null=False,
        help_text="Title of category."
    )
    parents = models.ManyToManyField(
        "self",
        blank=True,
        related_name="out_categories",
        default=None,
        symmetrical=False,
        help_text="Category that hierarchically upper then this category."
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_all_subcategories(self, used=None, recursively=None):
        all_ids = self.out_categories
        if not recursively:
            return all_ids.all()
        all_ids = set(all_ids.values_list('id', flat=True))

        used = set()
        while all_ids:
            current_id = all_ids.pop()
            sub_categories = Category.objects.get(id=current_id)\
                .out_categories.values_list(
                "id", flat=True
            )
            used.add(current_id)
            all_ids.update(sub_categories)

        return used
