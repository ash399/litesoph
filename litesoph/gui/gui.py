from tkinter import ttk                  # importing ttk which is used for styling widgets.
from tkinter import filedialog           # importing filedialog which is used for opening windows to read files.
from tkinter import messagebox

from typing import OrderedDict                        # importing subprocess to run command line jobs as in terminal.
import tkinter as tk
import pygubu

import os
import platform
import pathlib 


#---LITESOPH modules
from litesoph.gui.visual_parameter import myfont, create_design_feature
from litesoph.gui.logpanel import LogPanelManager
from litesoph.gui.menubar import get_main_menu_for_os
from litesoph.gui.user_data import get_remote_profile, update_proj_list, update_remote_profile_list
from litesoph.gui.viewpanel import ViewPanelManager
from litesoph.engines import TaskManager
from litesoph.common.ls_manager import LSManager 
from litesoph.common.project_manager import ProjectManager
from litesoph.common import models as m
from litesoph.gui.project_controller import ProjectController
from litesoph.gui import views as v
from litesoph.gui.views import StartPage
from litesoph.gui import actions
from litesoph.common.task import Task, TaskFailed
from litesoph.gui.navigation import ProjectList 


TITLE_FONT = ("Helvetica", 18, "bold")

DESINGER_DIR = pathlib.Path(__file__).parent

class GUIAPP:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.builder = pygubu.Builder()

        self.builder.add_from_file(str(DESINGER_DIR / "main_window.ui"))

        self.main_window = self.builder.get_object('mainwindow')

        menu_class = get_main_menu_for_os('Linux')
        menu = menu_class(self.main_window)
        self.main_window.config(menu=menu)

        self.treeview = self.builder.get_object('treeview1')

        self.input_frame = self.builder.get_object('inputframe')

        create_design_feature()

        self.task_input_frame = ttk.Frame(self.input_frame)
        self.task_input_frame.pack(fill=tk.BOTH, side=tk.LEFT)
        
        self.workflow_frame = ttk.Frame(self.input_frame)
        self.workflow_frame.pack(fill=tk.BOTH, side=tk.LEFT)
        
        self.proceed_button_frame = ttk.Frame(self.input_frame)
        self.proceed_button_frame.pack(fill=tk.BOTH, side=tk.BOTTOM)

        self.proceed_button = tk.Button(self.proceed_button_frame, text="Proceed",activebackground="#78d6ff",command=self.on_proceed_button)
        self.proceed_button['font'] = myfont()
        self.proceed_button.pack(side=tk.RIGHT, padx=10)
        
        self.project_window = None

        self.navigation = ProjectList(self)
        
        self.view_panel = ViewPanelManager(self)
        self.ls_manager = LSManager()

        self.engine = None

        self.setup_bottom_panel()

        self.status_engine = self.builder.get_variable('cengine_var')
        
        self.builder.connect_callbacks(self)

        
        self.laser_design = None

        self._frames = OrderedDict()
        
        self.project_controller = ProjectController(self)

        self._show_page_events()
        self._bind_event_callbacks()
        self.show_start_page()
        self.main_window.after(5000, self.save_data_repeat)
        #self.main_window.after(1000, self.update_project_dir_tree)

    def run(self):
        self.main_window.protocol("WM_DELETE_WINDOW", self.__on_window_close)
        self.main_window.mainloop()

    def __on_window_close(self):
        """Manage WM_DELETE_WINDOW protocol."""
        self.save_data()
        self.main_window.withdraw()
        self.main_window.destroy()

    def quit(self):
        """Exit the app if it is ready for quit."""
        self.__on_window_close()

    def setup_bottom_panel(self):

        self.log_panel = LogPanelManager(self)

    def save_data_repeat(self):
        self.save_data()
        self.main_window.after(30000, self.save_data_repeat)

    def save_data(self):
        self.ls_manager.save()

    def update_project_dir_tree(self):
        directory = self.ls_manager.current_project
        if directory:
            self.navigation.populate(directory)
        self.main_window.after(1000, self.update_project_dir_tree)
        
    def on_bpanel_button_clicked(self):
        self.log_panel.on_bpanel_button_clicked()

    def set_title(self, newtitle):
        self.current_title = newtitle
        default_title = 'LITESOPH - {0}'
        title = default_title.format(newtitle)
        self.main_window.wm_title(title)

    def _get_engine(self):
        return
        engine = self.ls_manager.get_previous_engine()
        if engine:
            self.engine = engine
            self.status_engine.set(self.engine)

    def _refresh_config(self,*_):
        """reads and updates the lsconfig object from lsconfig.ini"""
        self.ls_manager.read_lsconfig()
    
    def show_start_page(self):
        start_page = self.show_frame(StartPage)
        start_page.button_create_project.config(command= self.create_project_window)
        start_page.button_open_project.config(command= self._on_open_project)

    def show_frame(self, frame,*args, **kwargs):
        
        for widget in self.task_input_frame.winfo_children():
            widget.destroy()
        int_frame = frame(self.task_input_frame, *args, **kwargs)
        self._frames[frame]= int_frame
        self._frames.move_to_end(frame, last=False)
        int_frame.grid(row=0, column=0, sticky ='NSEW')
        int_frame.tkraise()

        return int_frame


    def _bind_event_callbacks(self):
        """binds events and specific callback functions"""
        event_callbacks = {
            actions.GET_MOLECULE : self.project_controller._on_get_geometry_file,
            actions.VISUALIZE_MOLECULE: self.project_controller._on_visualize,
            actions.CREATE_PROJECT_WINDOW:self.create_project_window,
            actions.OPEN_PROJECT : self._on_open_project,
            #actions.ON_PROCEED : self.project_controller._on_proceed,
            actions.REFRESH_CONFIG : self._refresh_config,
        }

        for event, callback in event_callbacks.items():
            self.main_window.bind_all(event, callback)                
    
    def _show_page_events(self):
        
        event_show_page= {
            #actions.SHOW_WORK_MANAGER_PAGE : self._show_workmanager_page,
            actions.SHOW_GROUND_STATE_PAGE: self. _on_ground_state_task,
            actions.SHOW_RT_TDDFT_DELTA_PAGE : self._on_rt_tddft_delta_task,
            actions.SHOW_RT_TDDFT_LASER_PAGE: self._on_rt_tddft_laser_task,
            actions.SHOW_SPECTRUM_PAGE : self._on_spectra_task,
            actions.SHOW_TCM_PAGE : self._on_tcm_task,
            actions.SHOW_MO_POPULATION_CORRELATION_PAGE : self._on_mo_population_task,
        #    actions.SHOW_MASKING_PAGE : self._on_masking_task
        }
        for event, callback in event_show_page.items():
            self.main_window.bind_all(event, callback)  

    def _show_workmanager_page(self, *_):

        self.show_frame(v.WorkManagerPage)
        if self.engine:
            self._frames[v.WorkManagerPage].engine.set(self.engine)

        self.show_project_summary()

    def _init_project(self, path):
        
        self.set_title(path.name)
        self.show_project_summary()
        update_proj_list(path)
        self._get_engine()
        self.navigation.create_project(path.name)
        

    def _on_open_project(self, *_):
        """creates dialog to get project path and opens existing project"""
        project_path = filedialog.askdirectory(title= "Select the existing Litesoph Project")
        if not project_path:
            return

        try:
            project_manager = self.ls_manager.open_project(pathlib.Path(project_path))
        except Exception as e:
            raise
            messagebox.showerror(title='Error', message = 'Unable open Project', detail =e)
            return
        self._init_project(pathlib.Path(project_path))
        self.show_project(project_manager)
        
    def create_project_window(self, *_):
        self.project_window = v.CreateProjectPage(self.main_window)
        self.project_window.button_project.config(command= self._on_create_project)   
        
    def _on_create_project(self, *_):
        """Creates a new litesoph project"""
        
        if not self.project_window:
            return

        project_name = self.project_window.get_value('proj_name')
        
        if not project_name:
            messagebox.showerror(title='Error', message='Please set the project name.')
            return

        project_path = filedialog.askdirectory(title= "Select the directory to create Litesoph Project")
        
        if not project_path:
            return

        project_path = pathlib.Path(project_path) / project_name
        
        try:
            project_manager = self.ls_manager.new_project(project_path.name, project_path.parent)
        except PermissionError as e:
            messagebox.showerror(title='Error', message = 'Premission denied', detail = e)
        except FileExistsError as e:
            messagebox.showerror(title='Error', message = 'Project already exists', detail =e)
        except Exception as e:
            raise
            messagebox.showerror(title='Error', message = 'Unknown problem', detail =e)
        else:
            self._init_project(project_path)
            self.engine = None
            self.project_window.destroy()
            self.show_project(project_manager)
                

    def show_project(self, project_manager: ProjectManager):
        self.project_controller.open_project(project_manager)

    def show_project_summary(self):
        summary = self.ls_manager.get_project_summary()
        self.view_panel.insert_text(summary, state='disabled')

    @staticmethod
    def _check_task_run_condition(task, network=False) -> bool:
        
        try:
           task.check_prerequisite(network)           
        except FileNotFoundError as e:
            return False
        else:
            return True
##----------------------Ground_State_task---------------------------------

    def _on_ground_state_task(self, *_):
        task_name = actions.GROUND_STATE
        self._frames[v.WorkManagerPage].refresh_var()
        self.show_frame(v.GroundStatePage, self.engine, task_name)
        self.ground_state_view = self._frames[v.GroundStatePage]
        if self.ground_state_view.engine.get() != self.engine:
            self.ground_state_view.engine.set(self.engine)
        self.ground_state_view.set_sub_button_state('disabled')
        self.ground_state_view.refresh_var()
        self.ground_state_view.set_label_msg('')
        self.view_panel.insert_text('')
        self.main_window.bind_all(f'<<Generate{task_name}Script>>', lambda _ : self._generate_gs_input(task_name, self.ground_state_view))

    def _generate_gs_input(self, task_name, view):
        inp_dict = view.get_parameters()
        if not inp_dict:
            return
        self.engine = inp_dict.pop('engine')
        self.ground_state_task = self.ls_manager.get_task(self.engine, task_name, inp_dict)
        self.ground_state_task.create_template()
        self.view_panel.insert_text(text=self.ground_state_task.template, state='normal')
        self.bind_task_events(task_name, self.ground_state_task, view)

##----------------------Time_dependent_task_delta---------------------------------

    def _on_rt_tddft_delta_task(self, *_):
        task_name = actions.RT_TDDFT_DELTA
        check = self.ls_manager.check_status(self.engine, task_name, self.status)
        
        if check[0]:
            self.status_engine.set(self.engine)    
        else:
            messagebox.showinfo(title= "Info", message=check[1])
            return
        self.show_frame(v.TimeDependentPage, self.engine, task_name)
        self.rt_tddft_delta_view = self._frames[v.TimeDependentPage]
        self.rt_tddft_delta_view.set_sub_button_state('disabled')
        self.rt_tddft_delta_view.update_engine_default(self.engine) 
        self.main_window.bind_all(f'<<Generate{task_name}Script>>', lambda _ : self._generate_td_input(task_name, self.rt_tddft_delta_view))

    def _generate_td_input(self, task_name, view):
        inp_dict = view.get_parameters()
        self.rt_tddft_delta_task = self.ls_manager.get_task(self.engine, task_name , inp_dict)
        self.rt_tddft_delta_task.create_template()
        self.view_panel.insert_text(text=self.rt_tddft_delta_task.template, state='normal')
        self.bind_task_events(task_name, self.rt_tddft_delta_task, view)

##----------------------Time_dependent_task_laser---------------------------------

    def _on_rt_tddft_laser_task(self, *_):
        task_name = actions.RT_TDDFT_LASER

        check = self.ls_manager.check_status(self.engine, task_name, self.status)
        
        if check[0]:
            self.status_engine.set(self.engine)    
        else:
            messagebox.showinfo(title= "Info", message=check[1])
            return
        self.show_frame(v.LaserDesignPage, self.engine, task_name)
        self.rt_tddft_laser_view = self._frames[v.LaserDesignPage]
        self.rt_tddft_laser_view.set_sub_button_state('disabled')
        self.rt_tddft_laser_view.engine = self.engine

        self.main_window.bind_all(f'<<Generate{task_name}Script>>', lambda _ :  self._generate_td_laser_input(task_name, self.rt_tddft_laser_view))
        self.main_window.bind_all('<<DesignLaser>>', self._on_design_laser)

    def _on_design_laser(self, *_):
        laser_desgin_inp = self.rt_tddft_laser_view.get_laser_pulse()
        self.laser_design = m.LaserDesignModel(laser_desgin_inp)
        self.laser_design.create_pulse()
        self.laser_design.plot_time_strength()

    def _on_choose_laser(self, *_):
        if not self.laser_design:
            messagebox.showerror(message="Laser is not set. Please choose the laser")
            return
        check = messagebox.askokcancel(message= "Do you want to proceed with this laser set up?")
        if check is True:
            self.laser_design.write_laser("laser.dat")
            return True
        else:
            self.laser_design = None 
            self._on_rt_tddft_laser_task()

    def _generate_td_laser_input(self, task_name, view):

        if not self._on_choose_laser():
            return
        view.set_laser_design_dict(self.laser_design.l_design)
        inp_dict = view.get_parameters()
        self.rt_tddft_laser_task = self.ls_manager.get_task(self.engine, task_name , inp_dict)
        self.rt_tddft_laser_task.create_template()
        self.view_panel.insert_text(text=self.rt_tddft_laser_task.template)
        self.bind_task_events(task_name, self.rt_tddft_laser_task, view)
##----------------------plot_delta_spec_task---------------------------------
    
    def _on_spectra_task(self, *_):
        task_name = actions.SPECTRUM
        check = self.ls_manager.check_status(self.engine, task_name, self.status)
        
        if check[0]:
            self.status_engine.set(self.engine)    
        else:
            messagebox.showinfo(title= "Info", message=check[1])
            return
        self.show_frame(v.PlotSpectraPage, self.engine, task_name)
        self.spectra_view = self._frames[v.PlotSpectraPage]
        self.spectra_view.engine = self.engine
        self.spectra_view.Frame1_Button2.config(state='active')
        self.spectra_view.Frame1_Button3.config(state='active')
        self.main_window.bind_all(f'<<SubLocal{task_name}>>', lambda _: self._on_spectra_run_local_button(task_name))
        self.main_window.bind_all(f'<<RunNetwork{task_name}>>', lambda _: self._on_spectra_run_network_button())
        self.main_window.bind_all(f'<<Show{task_name}Plot>>', lambda _:self._on_plot_button(self.spectra_view ,self.spectra_task))

    def _on_spectra_run_local_button(self, task_name, *_):
        
        inp_dict = self.spectra_view.get_parameters()
        self.spectra_task = self.ls_manager.get_task(self.engine, task_name, inp_dict)
        self.status.set_new_task(self.engine, self.spectra_task.task_name)
        self.status.update(f'{self.engine}.{self.spectra_task.task_name}.script', 1)
        self.status.update(f'{self.engine}.{self.spectra_task.task_name}.param',self.spectra_task.user_input)

        self.spectra_task.prepare_input()
        self._run_local(self.spectra_task, np=1)
        

##----------------------compute---tcm---------------------------------

    def _on_tcm_task(self, *_):
        task_name = actions.TCM
        check = self.ls_manager.check_status(self.engine, task_name , self.status)
        
        if check[0]:
            self.status_engine.set(self.engine)    
        else:
            messagebox.showinfo(title= "Info", message=check[1])
            return

        self.show_frame(v.TcmPage, task_name)
        self.tcm_view = self._frames[v.TcmPage]
        self.tcm_view.engine_name.set(self.engine)
        
        self.main_window.bind_all(f'<<SubLocal{task_name}>>', lambda _: self._on_tcm_run_local_button(task_name))
        self.main_window.bind_all(f'<<RunNetwork{task_name}>>', lambda _: self._on_tcm_run_network_button())
        self.main_window.bind_all(f'<<Show{task_name}Plot>>', lambda _: self._on_plot_button(self.tcm_view, self.tcm_task))

    def _on_tcm_run_local_button(self, task_name, *_):
        
        inp_dict = self.tcm_view.get_parameters()
        self.tcm_task = self.ls_manager.get_task(self.engine, task_name, inp_dict)
        self.tcm_task.prepare_input()
        self.status.set_new_task(self.engine,self.tcm_task.task_name)
        self.status.update(f'{self.engine}.{self.tcm_task.task_name}.script', 1)
        self.status.update(f'{self.engine}.{self.tcm_task.task_name}.param',self.tcm_task.user_input)

        self._run_local(self.tcm_task,np=1 )
        

##-------------------------------population task-------------------------------------------------------------

    def _on_mo_population_task(self, *_): 
        task_name = actions.MO_POPULATION      
        self.show_frame(v.PopulationPage,self.engine, task_name)
        self.mo_population_view = self._frames[v.PopulationPage]
        self.mo_population_view.engine = self.engine
        self.main_window.bind_all(f'<<SubLocal{task_name}>>', lambda _: self._on_mo_population_run_local_button(task_name))
        self.main_window.bind_all(f'<<Plot{task_name}>>', lambda _:self._on_plot_button(self.mo_population_view,self.mo_population_task))

    def _on_mo_population_run_local_button(self, task_name, *_):
        
        inp_dict = self.mo_population_view.get_parameters()
        self.mo_population_task = self.ls_manager.get_task(self.engine, task_name, inp_dict)
        self.status.set_new_task(self.engine, self.mo_population_task.task_name)
        self.status.update(f'{self.engine}.{self.mo_population_task.task_name}.script', 1)
        self.status.update(f'{self.engine}.{self.mo_population_task.task_name}.param',self.mo_population_task.user_input)

        self.mo_population_task.prepare_input()
        self._run_local(self.mo_population_task, np=1)

##-------------------------------masking task-------------------------------------------------------------

    def _on_masking_task(self, *_): 
        task_name = actions.MASKING     
        self.show_frame(v.MaskingPage,self.engine, task_name)
        self.masking_view = self._frames[v.MaskingPage]
        self.masking_view.engine = self.engine
        self.mask_task = self.ls_manager.get_task(self.engine, task_name, user_input={})
        self.main_window.bind_all(f'<<SubLocal{task_name}>>', lambda _: self._on_masking_page_compute(self.masking_view,self.mask_task))
        self.main_window.bind_all(f'<<Plot{task_name}>>', lambda _:self._on_plot_dm_file(self.masking_view,self.mask_task))
        
    def _on_masking_page_compute(self,view, task, *_):
        inp_dict = view.get_parameters()
        txt = task.get_energy_coupling_constant(**inp_dict)
        self.view_panel.insert_text(text= txt, state= 'disabled')

    def _on_plot_dm_file(self,view, task, *_):
        inp_dict = view.get_parameters()
        task.plot(**inp_dict)
##-----------------------------------------------------------------------------------------------------------##
    
    def on_proceed_button(self):
        #self.workflow_controller.next()
        pass

    def view_input_file(self, task:Task):
        self.view_panel.insert_text(task.template)
    
    def bind_task_events(self, task_name, task , view):
        self.main_window.bind_all(f'<<Save{task_name}Script>>', lambda _ : self._on_save_button(task, view))
        self.main_window.bind_all(f'<<SubLocal{task_name}>>', lambda _ : self._on_run_local_button(task))
        self.main_window.bind_all(f'<<SubNetwork{task_name}>>', lambda _ : self._on_run_network_button(task))
    
    def _on_save_button(self, task:Task, view, *_):
        template = self.view_panel.get_text()
        task.write_input(template)
        self.status.set_new_task(self.engine, task.task_name)
        self.status.update(f'{self.engine}.{task.task_name}.script', 1)
        self.status.update(f'{self.engine}.{task.task_name}.param',task.user_input)
        if task.task_name == 'ground_state':
            self.status_engine.set(self.engine)
        view.set_sub_button_state('active')
        view.set_label_msg('saved')
    
    def _on_run_network_button(self, task:Task, *_):

        if not self._check_task_run_condition(task):
            messagebox.showerror(message="Input not saved. Please save the input before job submission")
            return
        self.job_sub_page = v.JobSubPage(self.task_input_frame, task.task_name , 'Network')
        self.job_sub_page.grid(row=0, column=0, sticky ="nsew")
        remote = get_remote_profile()
        if remote:
            self.job_sub_page.set_network_profile(remote)
        self.job_sub_page.set_run_button_state('disable')
        self.job_sub_page.bind(f'<<Run{task.task_name}Network>>', lambda _: self._run_network(task))
        self.job_sub_page.bind(f'<<View{task.task_name}NetworkOutfile>>', lambda _: self._on_out_remote_view_button(task))
        self.job_sub_page.bind(f'<<Save{task.task_name}Network>>',lambda _: self._on_save_job_script(task, self.job_sub_page))
        self.job_sub_page.bind(f'<<Create{task.task_name}NetworkScript>>', lambda _: self._on_create_remote_job_script(task, task.task_name))
    
    def _on_run_local_button(self, task:Task, *_):

        if not self._check_task_run_condition(task):
            messagebox.showerror(message="Input not saved. Please save the input before job submission")
            return
        self.job_sub_page = v.JobSubPage(self.task_input_frame, task.task_name, 'Local')
        self.job_sub_page.grid(row=0, column=0, sticky ="nsew")
        self.job_sub_page.set_run_button_state('disable')
        
        self.job_sub_page.bind(f'<<Run{task.task_name}Local>>', lambda _: self._run_local(task))
        self.job_sub_page.bind(f'<<View{task.task_name}LocalOutfile>>', lambda _: self._on_out_local_view_button(task))
        self.job_sub_page.bind(f'<<Save{task.task_name}Local>>',lambda _: self._on_save_job_script(task, self.job_sub_page))
        self.job_sub_page.bind(f'<<Create{task.task_name}LocalScript>>', lambda _: self._on_create_local_job_script(task, task.task_name))
    
    def _on_plot_button(self,view, task: Task, *_):
        
        param = {}
        try:
            get_param_func = getattr(view, 'get_plot_parameters')
        except AttributeError:
            pass
        else:
            param = get_param_func()
        
        try:
            task.plot(**param)
        except Exception as e:
            messagebox.showerror(title='Error', message="Error occured during plotting", detail= e)

    def _run_local(self, task: Task, np=None):

        if np:
            sub_job_type = 0
            cmd = 'bash'
        else:
            np = self.job_sub_page.get_processors()
            sub_job_type = self.job_sub_page.sub_job_type.get()

            cmd = self.job_sub_page.sub_command.get()
            
        if sub_job_type == 1:
            
            if not cmd:
                messagebox.showerror(title="Error", message=" Please provide submit command for queue submission")
                self.job_sub_page.set_run_button_state('active')
                return
        else:
           if cmd != 'bash':
                messagebox.showerror(title="Error", message=" Only bash is used for command line execution")
                self.job_sub_page.set_run_button_state('active')
                return

        task.set_submit_local(np)
    

        try:
            task.run_job_local(cmd)
        except FileNotFoundError as e:
            messagebox.showerror(title='yes',message=e)
            return
        except Exception as e:
            messagebox.showerror(title = "Error",message=f'There was an error when trying to run the job', detail = f'{e}')
            return
        else:
            if task.local_cmd_out[0] != 0:
                self.status.update(f'{self.engine}.{task.task_name}.sub_local.returncode', task.local_cmd_out[0])
                messagebox.showerror(title = "Error",message=f"Job exited with non-zero return code.", detail = f" Error: {task.local_cmd_out[2]}")
            else:
                self.status.update(f'{self.engine}.{task.task_name}.sub_local.returncode', 0)
                self.status.update(f'{self.engine}.{task.task_name}.sub_local.n_proc', np)
                self.status.update(f'{self.engine}.{task.task_name}.done', True)
                messagebox.showinfo(title= "Well done!", message='Job completed successfully!')
                

    def _on_out_local_view_button(self,task: Task, *_):

        try:
            log_txt = task.get_engine_log()
        except TaskFailed:
            messagebox.showinfo(title='Info', message="Job not completed.")
            return
            
        self.view_panel.insert_text(log_txt, 'disabled')


    def _run_network(self, task: Task):

        try:
            task.check_prerequisite(network = True)
        except FileNotFoundError as e:
            messagebox.showerror(title = "Error", message = e)
            self.job_sub_page.set_run_button_state('active')
            return

        sub_job_type = self.job_sub_page.sub_job_type.get()

        cmd = self.job_sub_page.sub_command.get()
        if sub_job_type == 1:
            
            if not cmd:
                messagebox.showerror(title="Error", message=" Please provide submit command for queue submission")
                self.job_sub_page.set_run_button_state('active')
                return
        else:
           if cmd != 'bash':
                messagebox.showerror(title="Error", message=" Only bash is used for command line execution")
                self.job_sub_page.set_run_button_state('active')
                return

        
        login_dict = self.job_sub_page.get_network_dict()
        update_remote_profile_list(login_dict)
        
        try:
            task.connect_to_network(hostname=login_dict['ip'],
                                    username=login_dict['username'],
                                    password=login_dict['password'],
                                    port=login_dict['port'],
                                    remote_path=login_dict['remote_path'])
        except Exception as e:
            messagebox.showerror(title = "Error", message = 'Unable to connect to the network', detail= e)
            self.job_sub_page.set_run_button_state('active')
            return
        try:
            task.submit_network.run_job(cmd)
        except Exception as e:
            messagebox.showerror(title = "Error",message=f'There was an error when trying to run the job', detail = f'{e}')
            self.job_sub_page.set_run_button_state('active')
            return
        else:
            if task.net_cmd_out[0] != 0:
                self.status.update(f'{self.engine}.{task.task_name}.sub_network.returncode', task.net_cmd_out[0])
                messagebox.showerror(title = "Error",message=f"Error occured during job submission.", detail = f" Error: {task.net_cmd_out[2]}")
            else:
                self.status.update(f'{self.engine}.{task.task_name}.sub_network.returncode', 0)
                messagebox.showinfo(title= "Well done!", message='Job submitted successfully!')


    def _get_remote_output(self, task: Task):
        task.submit_network.download_output_files()
        self.status.update(f'{self.engine}.{task.task_name}.done', True)

    def _on_create_local_job_script(self, task: Task, *_):
        np = self.job_sub_page.processors.get()
        b_file =  task.create_job_script(np)
        self.view_panel.insert_text(b_file, 'normal')

    def _on_create_remote_job_script(self, task: Task, *_):
        np = self.job_sub_page.processors.get()
        rpath = self.job_sub_page.rpath.get()
        if rpath:
            b_file = task.create_job_script(np, remote_path=rpath)
        else:
            messagebox.showerror(title="Error", message="Please enter remote path")
            return
        self.view_panel.insert_text(b_file, 'normal')
       
    def _on_save_job_script(self,task :Task,view, *_):
        view.set_run_button_state('active')
        txt = self.view_panel.get_text()
        task.write_job_script(txt)

    def _on_out_remote_view_button(self,task, *_):
        
        try:
            exist_status, stdout, stderr = task.net_cmd_out
        except AttributeError:
            return

        print("Checking for job completion..")
        if task.submit_network.check_job_status():

            print('job Done.')
            self._get_remote_output(task)   
            log_txt = task.get_engine_log()
            self.view_panel.insert_text(log_txt, 'disabled')

        else:
            get = messagebox.askyesno(title='Info', message="Job not commpleted.", detail= "Do you what to download engine log file?")

            if get:
                task.submit_network.get_output_log()
                log_txt = task.get_engine_log()
                self.view_panel.insert_text(log_txt, 'disabled')
            else:
                return                

#--------------------------------------------------------------------------------        
if __name__ == '__main__':

    app = GUIAPP()
    app.run()
