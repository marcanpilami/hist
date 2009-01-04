#coding: UTF-8

"""
    Event handlers for keeping track of the modifications made on historised objects.
    These functions are private to the hist application.
    
    @author: Marc-Antoine Gouillart
    @copyright: Marc-Antoine Gouillart, 2009
    @license: GNU GPL v3
    
"""

## Django imports
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.signals import pre_save

## Hist imports
from exceptions import *
from models import Essence
from helpers import ModelDiff
from helpers_copy import _copy_object


def __instance_should_be_historised(instance):
    """
        Checks whether an object should be followed by hist.
    
        @param instance: the object that was modified
        @return: True or False
    """
    try:
        history_model = instance._meta.history_model
    except AttributeError:
        return False
    try:
        if instance._meta.history_disabled:
            return False
    except AttributeError:
        pass
    ## Check it is not a "blank" save
    try:
        if not original.modifications.is_modified():
            return False
    except:
        pass # first save
    return True


def after_save_event_handler(sender, instance, **kwargs):
    """Signal handler for creations"""
    ## Check this object really should be followed by hist
    if not __instance_should_be_historised(instance):
        return
    history_model = instance._meta.history_model
    
    ## Check it is a new object
    try:
        instance.current_version
    except:
        _copy_object(instance, 'creation', 0, u'création de l\'objet')



def before_save_event_handler(sender, instance, **kwargs):
    """Signal handler for updates"""
    ## Check this object really should be followed by hist
    if not __instance_should_be_historised(instance):
        return
    history_model = instance._meta.history_model
    
    ## Check it is an update and not a creation
    if not instance.id:
        return
    
    ## Current version
    version = instance.current_version + 1
    
    ## Create a new history object with the data
    _copy_object(instance, 'update', version, u'mise à jour sans commentaire')



def before_delete_event_handler(sender, instance, **kwargs):
    """signal handler for deletions"""
    ## Check this object really should be followed by hist
    if not __instance_should_be_historised(instance):
        return
    history_model = instance._meta.history_model
    
    ## Deleted version
    version = instance.current_version + 1
    avatar = instance.current_avatar
    
    ## Reference the deletion and link it to the latest avatar of the object
    ho = instance._meta.history_model(history_action = 'deletion',
                                     history_version = version, 
                                     history_comment = u'destruction sans commentaire',
                                     history_active_object = None,
                                     history_linked_to_version = avatar,
                                     essence = avatar.essence)
    ho.save()
  
    ## Remove all history FK, so that the deletion won't delete the avatars
    for history_object in instance.version_set.all():
        history_object.history_active_object = None
        history_object.save()
