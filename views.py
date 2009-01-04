#coding: UTF-8

"""
    Sample views for the history application.
    These views give an outlook on the different history objects. 
    
    @author: Marc-Antoine Gouillart
    @copyright: Marc-Antoine Gouillart, 2009
    @license: GNU GPL v3
    
"""

from models import *
from django.contrib.contenttypes.models import ContentType

from django.shortcuts import render_to_response


def all_versions(request):
    """displays the history of all active objects of every model"""
    models = []
    for ct in ContentType.objects.all():
        model = ct.model_class()
        try:
            if not model._meta.history_model:
                continue # _meta.history_model exists but is not correctly set
        except AttributeError:
            continue # _meta.history_model doens't exist, which means this model is not versionned
        
        models.append({'model':model,'objects':model.objects.all()})
        
    return render_to_response('all_versions.html', {'models':models})    
    
    
def all_history(request):
    """diplays the full history of all objects from all models, including deleted ones"""
    models = []
    for ct in ContentType.objects.all():
        model = ct.model_class()
        if model.__class__ != HistoryModelBase:
            continue
        models.append(model)
    
    return render_to_response('all_history.html', {'models':models})


def all_tags(request):
    """Shows all tags and their content"""
    return render_to_response('all_tags.html', {'tags':Level.objects.all()})


def avatar_detail(request, essence_id, version):
    av = None
    for a in Avatar.objects.filter(essence__id = int(essence_id)):
        if a.history_model.history_version == int(version):
            av = a.history_model
            break
    
    vals=[]
    for field in av._meta.fields + av._meta.many_to_many:
        if field.__class__.__name__ == 'ManyToManyField':
            vals.append({'name':field.name, 'value':getattr(av, field.name).all()})
        else:
            vals.append({'name':field.name, 'value':getattr(av, field.name)})
                    
    return render_to_response('avatar_detail.html', {'avatar':av, 'vals':vals})                                         