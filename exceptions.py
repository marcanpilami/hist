#coding: UTF-8

"""
    All the exceptions thrown by the hist application.
    Those exceptions are part of the API.
    
    @author: Marc-Antoine Gouillart
    @copyright: Marc-Antoine Gouillart, 2009
    @license: GNU GPL v3
    
"""

class HistoryException(Exception):
    pass


class DeletedObject(HistoryException):
    def __init__(self, history_object):
        self.history_object = history_object
    def __str__(self):
        return 'L\'objet %s de l\'historique ne correspond plus a un objet actif' %self.history_object
    
    
class NoHistoryModel(HistoryException):
    def __init__(self, instance):
        self.instance = instance
    def __str__(self):
        return 'L\'objet %s n\'est pas suivi en modifications' %self.instance

class UnknownVersion(HistoryException):
    def __init__(self, instance, version):
        self.instance = instance
        self.version = version
    def __str__(self):
        return 'L\'objet %s n\'a pas de version %s' %(self.instance, self.version)
    
