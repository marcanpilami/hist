#coding: UTF-8


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
    