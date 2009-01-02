#coding: UTF-8

"""
    History module.
    
    @author: Marc-Antoine Gouillart
    @copyright: Marc-Antoine Gouillart, 2008
    @license: GNU GPL v3
    
    @note: inspired by the Django admin interface and a proof-of-concept demonstrator of dynamic model creation
           at http://code.google.com/p/django-history-tables/ (GPL v3)
"""
    
## Python imports
import copy
import datetime

## Django imports
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.signals import pre_save, post_save, pre_delete
from django.contrib.contenttypes.models import ContentType
import django.dispatch

## Hist imports
from exceptions import *
#from handlers import before_save_event_handler, after_save_event_handler, before_delete_event_handler
from helpers import _getCurrentVersion, _diffWithPreviousVersion, _getCurrentVersionObject, _revert_instance_to_version, _getObjectAvatar, _diffWithCurrentVersion



###############################################################################
## Specific signals
###############################################################################

ready_to_delete = django.dispatch.Signal(providing_args=['instance',])



###############################################################################
## Metaclass
###############################################################################

class HistoryModelBase(ModelBase):
    def __new__(cls, name, bases, dct):
        new_class = ModelBase.__new__(cls, name, bases, dct)

        if 'historized_model' in dct:
            ## Retrive the spied upon model
            spied_model = dct['historized_model']
            
            ## Register the model used for historisation into the spied-upon model's Meta class. 
            spied_model._meta.history_model = new_class
            
            ## Copy basic fields
            for field in spied_model._meta.fields:
                
                ## PK handling
                if field.primary_key:  
                    _field = copy.copy(field)
                    if field.__class__.__name__ == 'AutoField': # note: an autofield is always the PK
                        _field = models.IntegerField(max_length = 100)
                    if field.name == 'id':
                        _field.name = 'history_id'
                    
                    _field.primary_key = False
                    if _field.unique:
                        _field.unique = False
                    _field.history_field = True
                    new_class.add_to_class(_field.name, _field)
                    def __getOldPK(self):
                        return getattr(self, self._meta.HOP)
                    new_class.history_old_pk = property(__getOldPK)
                    new_class._meta.HOP = _field.name
                    continue
                
                ## FK handling
                if field.__class__.__name__ == 'ForeignKey':
                    _field = models.ForeignKey(Essence, blank=True, null=True, related_name = r'history_' + field.name + r'_avatar_set')
                    _field.history_field = True
                    _field.name = field.name
                    new_class.add_to_class(_field.name, _field)
                    continue
                
                ## Casual fields handling
                _field = copy.copy(field)
                _field.history_field = True
                if _field.unique:
                    _field.unique = False
                new_class.add_to_class(_field.name, _field)
                
            ## Copy many to many fields 
            for mm in spied_model._meta.many_to_many:
                _mm = models.ManyToManyField(Essence, null = True, blank = True, related_name = r'history_' + mm.name + r'_avatar_set')
                _mm.history_field = True
                _mm.name = mm.name
                new_class.add_to_class(_mm.name, _mm)
            
            ## Create a relationship to the current version object
            new_class.add_to_class('history_active_object', 
                                   models.ForeignKey(spied_model, blank = True, null = True, 
                                                     related_name = 'version_set'))
            
            ## Create an optional relationship to another version objet
            new_class.add_to_class('history_linked_to_version',
                                   models.ForeignKey(new_class, blank = True, null = True, 
                                                     related_name = 'history_used_by_version_set'))
            
            ## Register the signal listener
            #pre_save.connect( before_save_event_handler, sender = spied_model)
            #post_save.connect(after_save_event_handler,  sender = spied_model)
            #pre_delete.connect(before_delete_event_handler, sender = spied_model)
            #ready_to_delete.connect(before_delete_event_handler, sender = spied_model)
            
            ## Add attributes to the spied upon object
            spied_model.current_version = property(_getCurrentVersion)
            spied_model.current_avatar = property(_getCurrentVersionObject)
            spied_model.essence = property(_getObjectAvatar)
            spied_model.modifications = property(_diffWithCurrentVersion)
            
            ## Add helper functions to the spied upon object
            spied_model.revert_to = _revert_instance_to_version
            
            ## delete overload, but we must take into account an optional overload by the user himself
            spied_model.history_delete = spied_model.delete  
            def delete(self):
                ready_to_delete.send(sender = spied_model, instance=self)
                self.history_delete()
            spied_model.delete = delete
            
        ## End : return the model
        return new_class
    


###############################################################################
## History base objects
###############################################################################

class Essence(models.Model):
    def __unicode__(self):
        return u'objet %s' %self.id


class Avatar(models.Model):
    """
        Base class for all history objects, so that we may have a convenient handle on them
        All it does is retain information on how to access the real history model.
    """ 
    ## This object is an avatar of an essence :
    essence = models.ForeignKey(Essence)
    
    ## Polymporphism handling
    history_final_type = models.ForeignKey(ContentType, editable = False) 
    def save(self, *args, **kwargs) :
        if not self.id: # only run at creation
            self.history_final_type = ContentType.objects.get_for_model(type(self))
        super(Avatar, self).save(*args, **kwargs) 
    def _history_getTrueModel(self):
        return self.history_final_type.get_object_for_this_type(id=self.id) 
    history_model = property(_history_getTrueModel)
    
    
class HistoryModel(Avatar):
    """Abstract model for historisation. The history fields are created at runtime through HistoryModelBase"""
    __metaclass__ = HistoryModelBase

    history_datetime = models.DateTimeField(default=datetime.datetime.now)
    history_comment = models.CharField(max_length = 1024, blank = True, null = True) # comment on history item
    history_action = models.CharField(max_length=9, 
                            choices = (('creation','creation'), ('update','update'), ('deletion','deletion'),))
    history_version = models.IntegerField(max_length = 100)
    
    def __unicode__(self):
        return u'Objet sauvé le %s' %(self.history_datetime)
    
    def delete(self, *args, **kwargs):
        print 'ooooo'
        pass
    
    class Meta:
        abstract = True # Don't create any tables for this model. ("simple" inheritance, i.e. abstract model)
        ordering = ['history_version',]
        
    diff_prev = property(_diffWithPreviousVersion)


#TODO: redirect M2M history to historized objects rather than the active one ?



###############################################################################
## TAGS
###############################################################################

class LevelManager(models.Manager):
    def snap(self):
        """
            Creates a tag from all versionned objects in the db.
            @note: this function hits the database very hard.
            @return: the new Level object
        """
        ## Create new level
        l = Level(comment = u'magnifique niveau de version')
        l.save()
        
        for ct in ContentType.objects.all():
            ## Check this is a versionned model
            model = ct.model_class()
            try:
                if not model._meta.history_model:
                    continue # _meta.history_model exists but is not correctly set
            except AttributeError:
                continue # _meta.history_model doesn't exist, which means this model is not versionned
            
            ## Reference all latest objects
            for object in model.objects.all():
                l.versionned_objects.add(object.current_avatar)
        l.save()
        return l

 
class Level(models.Model):
    """Version level. Contains links to all history objects"""
    level = models.AutoField(primary_key = True)
    date_time = models.DateTimeField(default=datetime.datetime.now)
    comment = models.CharField(max_length = 200)
    versionned_objects = models.ManyToManyField(Avatar, related_name = 'history_level_set') 
    
    objects = LevelManager()
    