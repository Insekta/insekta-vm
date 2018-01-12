from django.db import models

from insektavm.base.models import UserToken


class AssignedIPAddress(models.Model):
    user_token = models.OneToOneField(UserToken, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField(protocol='ipv4', unique=True)

    def __str__(self):
        return '{} -> {}'.format(self.user_token, self.ip_address)
