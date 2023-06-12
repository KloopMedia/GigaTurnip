from api.models import BaseDatesModel


class Case(BaseDatesModel):

    def __str__(self):
        return str("Case #" +
                   str(self.id))
