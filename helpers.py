#coding: UTF-8

"""
    Private functions for the hist application. 
    These functions are not part of the API.
    
    @author: Marc-Antoine Gouillart
    @copyright: Marc-Antoine Gouillart, 2009
    @license: GNU GPL v3
"""

from exceptions import *
from helpers_copy import _is_history_field


def _getCurrentVersion(object):
    return object.version_set.latest('history_datetime').history_version

def _getCurrentVersionObject(object):
    return object.version_set.latest('history_datetime')

def _getObjectEssence(monitored_object):
    return monitored_object.version_set.all()[0].essence


class ModelDiff:
    def __init__(self, reference, object):
        """
            Constructor for the ModelDiff class.
            
            @param reference: the reference object (Avatar or instance of an historised model)
            @param object: the object to compare (same class as the 'reference' parametre)
        """
        self.dict = {}
        try:
            reference.history_model # replaces the test: isinstance(reference, Avatar)
        except AttributeError:
            ## no history_model means this is not an avatar
            self.__diffInstances(reference, object)
            return
        self.__diffAvatars(reference, object)
    
    def is_modified(self):
        return self.dict.__len__() != 0
        
    def __unicode__(self):
        res = u''
        for key in self.dict.keys():
            res += u'Le champ "%s" est passé de "%s" à "%s". ' %(key, self.dict[key][0], self.dict[key][1])
        return res

    def __diffAvatars(self, av1, av2):
        """
            Compares two avatars, and completes self data
        """        
        ## Tests
        if (not isinstance(av2, av1.__class__)) and (not isinstance(av1, av2.__class__)):
            raise Exception('Impossible de comparer des objets de classes differentes')
        
        ## Compare fields
        for field in av1._meta.fields + av1._meta.many_to_many:
            ## Check this is a field from the original model
            if not _is_history_field(field):
                continue
            
            ## Compare values
            val_1 = getattr(av1, field.name)
            val_2 = getattr(av2, field.name)
            
            if field.__class__.__name__ != 'ManyToManyField' and val_1 != val_2:
                self.dict[field.name] = [val_1, val_2]
            elif field.__class__.__name__ == 'ManyToManyField':
                l1 = [object for object in val_1.all().order_by('avatar')]
                l2 = [object for object in val_2.all().order_by('avatar')]
                if l1 != l2:
                    self.dict[field.name] = [l1, l2]


    def __diffInstances(self, av1, av2):
        """
            Compares two instances, and completes self data
        """
        ## Tests
        if (not isinstance(av2, av1.__class__)) and (not isinstance(av1, av2.__class__)):
            raise Exception('Impossible de comparer des objets de classes differentes')
        
        ## Compare fields
        for field in av1._meta.fields + av1._meta.many_to_many:
            ## Compare values
            val_1 = getattr(av1, field.name)
            val_2 = getattr(av2, field.name)
            
            if field.__class__.__name__ != 'ManyToManyField' and val_1 != val_2:
                self.dict[field.name] = [val_1, val_2]
            elif field.__class__.__name__ == 'ManyToManyField':
                l1 = [object for object in val_1.all().order_by('id')]
                l2 = [object for object in val_2.all().order_by('id')]
                if l1 != l2:
                    self.dict[field.name] = [l1, l2]


def _diffWithPreviousVersion(avatar):
    """@return: a ModelDiff object comparing with the previous avatar (selected by datetime)
    @raise exception: if there is no previous avatar""" 
    prev = avatar.get_previous_by_history_datetime(essence = avatar.essence)
    return ModelDiff(prev, avatar)

def _diffWithCurrentVersion(instance):
    try:
        current_saved_object = instance.current_avatar.history_active_object
    except:
        raise Exception('objet jamais sauvegarde')
    return ModelDiff(current_saved_object, instance)
