from django.db import models

class UserAccount(models.Model):
    id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    username = models.TextField(unique=True)
    password = models.TextField()
    first_name = models.TextField()
    last_name = models.TextField()
    is_logged = models.BooleanField(default=True,blank=False)
    created_date = models.DateTimeField(auto_now_add=True, auto_now=False,blank=False)

    def __str__(self):
        return self.name