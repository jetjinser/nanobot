from tortoise.models import Model
from tortoise import fields

class Suber(Model):
    id = fields.IntField(pk=True)
    chan = fields.TextField()
    group = fields.IntField()

    def __str__(self) -> str:
        return f"[{self.id}] {self.chan} :: {self.group}"

    class Meta:
        unique_together = (("group", "chan"),)

