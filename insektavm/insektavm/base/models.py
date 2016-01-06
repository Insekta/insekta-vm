from django.db import models


class UserToken(models.Model):
    username = models.CharField(max_length=120, unique=True)

    def __str__(self):
        return self.username
