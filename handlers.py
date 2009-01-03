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


def __copy_object(original, action_code, version, comment):
    """factorization of common copy code for all signal handlers"""
    ## Check it is not a "blank" save
    try:
        if action_code != 'delete' and not original.modifications.is_modified():
            return
    except:
        pass # first save
    
    ## Create HO object
    ho = original._meta.history_model(history_action = action_code,
                                     history_version = version, 
                                     history_comment = comment,
                                     history_active_object = original)
    
    ## Basic fields
    for field in original._meta.fields:
        ## Autofields
        if field.name == 'id':
            setattr(ho, 'history_id', getattr(original, field.name))
        ## FK
        elif field.__class__.__name__ == 'ForeignKey':
            try:
                if getattr(original, field.name)._meta.history_model:
                    setattr(ho, field.name, getattr(original, field.name).essence)
                    continue
                else:
                    continue ## The target object is not (yet) historised
            except AttributeError:
                continue
        ## Casual fields
        else:
            setattr(ho, field.name, getattr(original, field.name))
    
    ## Essence
    try:
        ho.essence = original.current_avatar.essence
    except:
        e = Essence()
        e.save()
        ho.essence = e
    
    ## M2M
    ho.save()    ## needed for M2M...
    for mm in original._meta.many_to_many:
        try: 
            # Try/catch is to check whether the target model is historized or not (or if there is nothing to historise)
            if getattr(original, mm.name).all()[0]._meta.history_model:
                print 'ici'
                print getattr(original, mm.name).all() 
                m2m_manager = getattr(ho, mm.name)
                for essence in [ ess.current_avatar.essence for ess in getattr(original, mm.name).all() ]:
                    print essence
                    m2m_manager.add(essence)
                print getattr(ho, mm.name).all()
                print 'fin'
                continue
            else:
                continue ## The target object is not (yet) historised
        except (AttributeError, IndexError):
            continue
    
    ## End
    ho.save()
    return ho


def after_save_event_handler(sender, instance, **kwargs):
    """Signal handler for creations"""
    ## Check this object really should be followed by hist
    try:
        history_model = instance._meta.history_model
    except AttributeError:
        return
    if not history_model:
        raise NoHistoryModel(instance)
    
    ## Check it is a new object
    try:
        instance.current_version
    except:
        __copy_object(instance, 'creation', 0, u'création de l\'objet')



def before_save_event_handler(sender, instance, **kwargs):
    """Signal handler for updates"""
    ## Check this object really should be followed by hist
    try:
        history_model = instance._meta.history_model
    except AttributeError:
        return
    if not history_model:
        raise NoHistoryModel(instance)
    
    ## Check it is an update and not a creation
    if not instance.id:
        return
         
    ## Get original object
    original = sender.objects.get(pk=instance.id)
 
    ## Check the object has really changed (not a "blank" call to save())
    #TODO: write this part (consider fields list)
    
    ## Current version
    version = instance.current_version + 1
    
    ## Create a new history object with the data
    __copy_object(instance, 'update', version, u'mise à jour sans commentaire')



def before_delete_event_handler(sender, instance, **kwargs):
    """signal handler for deletions"""
    ## Check this object really should be followed by hist
    try:
        history_model = instance._meta.history_model
    except AttributeError:
        return
    if not history_model:
        raise NoHistoryModel(instance)
    
    ## Deleted version
    version = instance.current_version + 1
    avatar = instance.current_avatar
    
    ## Reference the deletion and link it to the latest avatar of the object
    ho = instance._meta.history_model(history_action = 'delete',
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
