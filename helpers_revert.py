#coding: UTF-8

"""
    Private functions for the hist application. 
    These functions are not part of the API.
    
    @author: Marc-Antoine Gouillart
    @copyright: Marc-Antoine Gouillart, 2009
    @license: GNU GPL v3
"""

from exceptions import *
from helpers_copy import _copy_object


def _revert_to(avatar, fork = False):
    """
        Main restoration function.
        
        Restores an avatar into the active objects.
        If the object is still active, it is updated.
        If the object has been deleted, it is recreated.
        
        @raise DeletedObject: if a referenced object (FK, M2M) doesn't exist any more and hence prevents restoration.
        @param avatar: the archive to restore.
        @param fork: set to True to create a new object, unrelated to the copied target essence. 
    """  
    ## Target instance
    if not avatar.history_active_object or fork:
        instance = avatar.historized_model()
    else:
        instance = avatar.history_active_object
    
    ## Diable hist for the time being on this particular instance
    instance._meta.history_disabled = True
    
    ## Single value fields restoration
    for field in avatar._meta.fields:
        ## Check this is a field from the original model
        try:
            if not field.history_field:
                continue
        except AttributeError:
            continue
        
        ## FK handling
        if field.__class__.__name__ == 'ForeignKey':
            ## In that case, 'field' points to an essence object.
            ess = getattr(avatar, field.name)
            if not ess: continue
            
            ## This essence should still have active object, else this triggers an exception
            value = ess.avatar_set.all()[0].history_final_type.history_active_object
            
            ## Set the value
            setattr(instance, field.name, ao)
        
        ## Normal field handling
        else:
            value = getattr(avatar, field.name)
            
        ## Set the value
        setattr(instance, field.name, value)
   
    
    ## M2M restoration
    m2m = {}
    # Step 1 : check all the targets still exist, before saving the new/modified instance.
    for field in avatar._meta.many_to_many:
        m2m[field.name] = [ess.avatar_set.all()[0].history_final_type.history_active_object for ess in getattr(avatar, field.name).all()]
    
    # Step 2 : we're sure it will work, so save it all and reference the values
    instance.save()
    for field in m2m.keys():
        setattr(instance, field, m2m[field])
    instance.save()
    
    
    ## Restore the links to active objects in all avatars
    if not avatar.history_active_object and not fork:
        for av in avatar.essence.avatar_set.all():
            avc = av.history_final_type
            avc.history_active_object = instance
            avc.save()
    
    
    ## Log the restoration
    if fork:
        ho = _copy_object(instance, 'create', 0, u'fork de la version %s de l\'essence %s' %(avatar.history_version, avatar.essence.id))
    else:
        ho = _copy_object(instance, 'restoration', instance.current_version + 1, u'restauration de la version %s' %avatar.history_version)
    ho.history_linked_to_version = avatar
    ho.save()
    
    ## Re-enable hist
    instance._meta.history_disabled = False
    
    ## End
    return instance


def _revert_instance_to_version(instance, version):
    """
        Helper function for restoring a perticular version of an existing object.
       
        @param instance: the versionned object subect to restoration
        @param version: the version (either an integer or an avatar) to restore
       
        @see: _revert_to
    """
    history_object = version
    if isinstance(version, int):
        try:
            history_object = instance.version_set.get(history_version = version)
        except:
            raise UnknownVersion(instance, version) 
    
    if not isinstance(history_object, instance._meta.history_model):
        raise Exception('la version specifiee n est pas du bon type')
    
    _revert_to(history_object)
    

def _revert_latest_commit(instance):
    version = instance.current_version - 1
    print version
    _revert_instance_to_version(instance, version)


def _fork(object):
    ## The object may be an active instance of an historised model
    try:
        history_model = object._meta.history_model
        return _revert_to(object.current_avatar, True)
    except AttributeError:
        pass
    
    ## It may be an avatar
    return _revert_to(object, True)
     
    