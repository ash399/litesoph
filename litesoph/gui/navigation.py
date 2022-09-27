from pathlib import Path
import tkinter as tk
import tkinter.ttk as ttk
import collections

class ProjectList:

    def __init__(self, app):
        
        self.treedata = dict()
        self.current_path_list = []
        self.treeview = app.treeview
        
        self.treeview.bind('<<TreeviewOpen>>', self.open_node)
        
    def populate(self, project_path: Path):
        
        paths = [path for path in project_path.glob('**/*')]
        if not compare_list(paths, self.current_path_list):    
            rot = self.treeview.get_children()
            if rot:
                self.treeview.delete(rot)

            self.current_path_list = paths
            self.insert_node('', project_path.name, project_path)
        else:
            return

    def insert_node(self, parent, text, abspath):
        node = self.treeview.insert(parent, 'end', text=text, open=False)
        if Path.is_dir(abspath):
            self.treedata[node] = abspath
            self.treeview.insert(node, 'end')

    def open_node(self, event):
        node = self.treeview.focus()
        abspath = self.treedata.pop(node, None)
        if abspath:
            self.treeview.delete(self.treeview.get_children(node))
            for p in Path.iterdir(abspath):
                self.insert_node(node, p.name, Path.joinpath(abspath, p))

def compare_list(list1,list2):
        if(collections.Counter(list1)==collections.Counter(list2)):
            return True
        else:
            return False
