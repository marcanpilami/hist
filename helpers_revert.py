#coding: UTF-8

"""
    Private functions for the hist application. 
    These functions deal with everything related to applying a save (revert, fork, merge)
    These functions are not part of the API.
    
    @author: Marc-Antoine Gouillart
    @copyright: Marc-Antoine Gouillart, 2009
    @license: GNU GPL v3
"""

from exceptions import *
from helpers_copy import _copy_object, _is_history_field
import graph


def _revert_to(avatar, fork = False , merge = None):
    """
        Main restoration function.
        
        Restores an avatar into the active objects.
        If the object is still active, it is updated.
        If the object has been deleted, it is recreated.
        
        @raise DeletedObject: if a referenced object (FK, M2M) doesn't exist any more and hence prevents restoration.
        @param avatar: the archive to restore.
        @param fork: set to True to create a new object, unrelated to the copied target essence. 
        @param merge:  an object instance with which the avatar should be merged. 
        @note: if 'fork' is True, then 'merge' is ignored. 
    """
    ## Target instance
    if fork:
        instance = avatar.historized_model()
    elif merge:
        instance = merge
        #TODO: test same model as avatar
    elif not avatar.history_active_object:
        instance = avatar.historized_model()
    else:
        instance = avatar.history_active_object
    
    ## Diable hist for the time being on this particular instance
    instance._meta.history_disabled = True
    
    ## Single value fields restoration
    for field in avatar._meta.fields:
        ## Check this is a field from the original model
        if not _is_history_field(field):
            continue
        
        ## FK handling
        if field.__class__.__name__ == 'ForeignKey':
            ## In that case, 'field' points to an essence object.
            ess = getattr(avatar, field.name)
            if not ess: continue
            
            ## This essence should still have active object, else this triggers an exception
            value = ess.avatar_set.all()[0].history_model.history_active_object
        
        ## Normal field handling
        else:
            value = getattr(avatar, field.name)
            
        ## Set the value
        setattr(instance, field.name, value)
   
    
    ## M2M restoration
    m2m = {}
    # Step 1 : check all the targets still exist, before saving the new/modified instance.
    for field in avatar._meta.many_to_many:
        ## Check this is a field from the original model
        if not _is_history_field(field):
            continue

        ## Look for target
        m2m[field.name] = [ess.avatar_set.all()[0].history_model.history_active_object for ess in getattr(avatar, field.name).all()]
    
    # Step 2 : we're sure it will work, so save it all and reference the values
    instance.save()
    for field in m2m.keys():
        setattr(instance, field, m2m[field])
    instance.save()
    
    
    ## Restore the links to active objects in all avatars
    if not avatar.history_active_object and not fork and not merge:
        for av in avatar.essence.avatar_set.all():
            avc = av.history_final_type
            avc.history_active_object = instance
            avc.save()
    
    
    ## Log the operation
    try:
        if fork:
            ho = _copy_object(instance, 'create', 0, u'fork de la version %s de l\'essence %s' %(avatar.history_version, avatar.essence.id))
        elif merge:
            ho = _copy_object(instance, 'merge', instance.current_version + 1, u'merge avec la version %s de l\'essence %s' %(avatar.history_version, avatar.essence.id))
        else:
            ho = _copy_object(instance, 'restoration', instance.current_version + 1, u'restauration de la version %s' %avatar.history_version)
        ho.history_linked_to_version = avatar
        ho.save()
    except WontCopy:
        pass
    
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


def _merge(object_instance, avatar):
    """
        The content of 'avatar' will be merged into the 'object_instance' 
        (one new commit).
        @param object_instance: the instance that will receive the new data
        @param avatar: the source of the merged data
    """
    return _revert_to(avatar, False, object_instance)
    

def _load_tag(self):
        """
            Loads a level. All active objects are updated, missing objects are created.
        """        
        
        ## Build a graph with all relationships betwen objects, then do a topological sort
        di = graph.digraph()
        for av in self.versionned_objects.all():
            avatar = av.history_model
            
            ## Add the node to the graph
            if not di.has_node(avatar.essence.id):      ## It may have been created before through a relationship
                di.add_node(avatar.essence.id)
            
            ## Add edges towards linked objects
            for field in avatar._meta.fields + avatar._meta.many_to_many:
                # Check this field is an historised relationship
                if field.__class__.__name__ != 'ManyToManyField' and field.__class__.__name__ != 'ForeignKey':
                    continue
                try:
                    if not field.history_field:
                        continue
                except AttributeError:
                    continue
                
                # Extract target essences
                if field.__class__.__name__ == 'ManyToManyField':
                    target_essences = getattr(avatar, field.name).all()  
                if field.__class__.__name__ == 'ForeignKey':
                    target_essences = [getattr(avatar, field.name),]
                    if target_essences[0] == None:
                        target_essences = []
                
                # Add edges 
                for essence in target_essences:
                    ## Add the target node to the graph if it doesn't already exist
                    if not di.has_node(essence.id):
                        di.add_node(essence.id)
                    
                    ## Add the edge
                    di.add_edge(essence.id, avatar.essence.id)
        
        id_list = di.topological_sorting()      
        
        ## Restore the objects in the computed order
        for essence_id in id_list:
            avatar = self.versionned_objects.get(essence__id = essence_id).history_model
            _revert_to(avatar)    
    
