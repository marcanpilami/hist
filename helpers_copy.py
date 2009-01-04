#coding: UTF-8

"""
    
    
    @author: Marc-Antoine Gouillart
    @copyright: Marc-Antoine Gouillart, 2009
    @license: GNU GPL v3
"""

from django.db import models

class Essence(models.Model):
    """Clearly not at the right place"""
    def __unicode__(self):
        return u'objet %s' %self.id


def _is_history_field(field):
    """Check if an avatar field is from the original model"""
    try:
        if not field.history_field:
            return False
    except AttributeError:
        return False
    return True

def _copy_object(original, action_code, version, comment):
    """factorization of common copy code for all signal handlers"""
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
                m2m_manager = getattr(ho, mm.name)
                for essence in [ ess.current_avatar.essence for ess in getattr(original, mm.name).all() ]:
                    m2m_manager.add(essence)
                continue
            else:
                continue ## The target object is not (yet) historised
        except (AttributeError, IndexError):
            continue
    
    ## End
    ho.save()
    return ho

