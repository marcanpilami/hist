print "chargement module historique"

from handlers import before_save_event_handler, after_save_event_handler, before_delete_event_handler
from models import Essence, ready_to_delete
from django.db.models.signals import pre_save, post_save, pre_delete
import django.dispatch



###############################################################################
## Signal connections
###############################################################################

pre_save.connect( before_save_event_handler)
post_save.connect(after_save_event_handler)
#pre_delete.connect(before_delete_event_handler)
ready_to_delete.connect(before_delete_event_handler)
