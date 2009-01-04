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
            @param object: the object to compare
        """
        self.dict = {}
        self.__diff(reference, object)
    
    def is_modified(self):
        return self.dict.__len__() != 0
        
    def __unicode__(self):
        res = u''
        for key in self.dict.keys():
            res += u'Le champ "%s" est passé de "%s" à "%s". ' %(key, self.dict[key][0], self.dict[key][1])
        return res

    def __diff(self, o1, o2):
        ## Get field list
        try:
            o1.history_model    # only HM (ie avatars) have a history_model
            fields = o1._meta.fields + o1._meta.many_to_many
        except AttributeError:
            ## no history_model means this is not an avatar, so it *should* be an object instance
            try:
                fields = o1.current_avatar._meta.fields + o1.current_avatar._meta.many_to_many
            except:
                raise UndiffableObject(o1)
         
        ## Filter the fields
        f2 = []
        for f in fields:
            if _is_history_field(f):
                f2.append(f) 
           
        ## Compare fields
        for field in f2:
            ## Compare values
            val_1 = getattr(o1, field.name)
            val_2 = getattr(o2, field.name)
            
            if field.__class__.__name__ == 'ForeignKey': 
                if val_1 and val_1.__class__.__name__ != 'Essence':
                    val_1 = val_1.essence
                if val_2 and val_2.__class__.__name__ != 'Essence':
                    val_2 = val_2.essence   
                if val_1 != val_2:
                    self.dict[field.name] = [val_1, val_2]
            elif field.__class__.__name__ == 'ManyToManyField':             
                l1 = [essence for essence in val_1.all()]
                for ess in l1:
                    if ess.__class__.__name__ != 'Essence':
                        l1.remove(ess)
                        l1.append(ess.essence)
                l2 = [essence for essence in val_2.all()]
                for ess in l2:
                    if ess.__class__.__name__ != 'Essence':
                        l2.remove(ess)
                        l2.append(ess.essence)
                if l1 != l2:
                    self.dict[field.name] = [l1, l2]
            elif val_1 != val_2:
                self.dict[field.name] = [val_1, val_2]


def _diffWithPreviousVersion(avatar):
    """@return: a ModelDiff object comparing with the previous avatar (selected by datetime)
    @raise exception: if there is no previous avatar""" 
    prev = avatar.get_previous_by_history_datetime(essence = avatar.essence)
    return ModelDiff(prev, avatar)

def _diffWithCurrentVersion(instance):
    try:
        current_saved_object = instance.current_avatar
    except:
        raise UndiffableObject(instance)
    return ModelDiff(current_saved_object, instance)
