#coding: UTF-8

## Django imports
from django.db.models.signals import post_syncdb
from django.db import transaction
from django.db import models





def post_syncdb_handler(sender, **kwargs):
    print sender.__dict__
    print sender









## Listen to the syncdb signal
#post_syncdb.connect(post_syncdb_handler)
