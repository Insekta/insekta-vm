from django.db import models


RESOURCE_TYPE_CHOICES = (
    ('vmnet', 'Network of VMs'),
)


class Resource(models.Model):
    name = models.CharField(max_length=120)
    type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES)

    def __str__(self):
        return self.name