from django.db import models
# from django.contrib.auth.models import 
from account.models import UserAccount
# Create your models here.
class Garment(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField()
    brand = models.TextField()
    colour = models.TextField()
    country = models.TextField()
    size = models.TextField()
    status = models.BooleanField(blank=False)
    colour_name = models.TextField(default='WHITE')
    created_date = models.DateTimeField(auto_now_add=True, auto_now=False,blank=False)
    user_id = models.ForeignKey(UserAccount, on_delete = models.SET_NULL, null=True)
    # add userID in the future
    def __str__(self):
        return self.namename