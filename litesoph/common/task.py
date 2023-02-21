from typing import List, Any, Union
import pathlib
import re
import os
from abc import abstractmethod
from litesoph.common.job_submit import SubmitNetwork, SubmitLocal
from litesoph.common.data_sturcture.data_classes import TaskInfo

class TaskError(RuntimeError):
    """Base class of error types related to any TASK."""


class TaskSetupError(TaskError):
    """Calculation cannot be performed with the given parameters.

    Typically raised before a calculation."""



class InputError(TaskSetupError):
    """Raised if inputs given to the calculator were incorrect.

    Bad input keywords or values, or missing pseudopotentials.

    This may be raised before or during calculation, depending on
    when the problem is detected."""


class TaskFailed(TaskError):
    """Calculation failed unexpectedly.

    Reasons to raise this error are:
      * Calculation did not converge
      * Calculation ran out of memory
      * Segmentation fault or other abnormal termination
      * Arithmetic trouble (singular matrices, NaN, ...)

    Typically raised during calculation."""


class ReadError(TaskError):
    """Unexpected irrecoverable error while reading calculation results."""


class TaskNotImplementedError(NotImplementedError):
    """Raised if a calculator does not implement the requested property."""


class PropertyNotPresent(TaskError):
    """Requested property is missing.

    Maybe it was never calculated, or for some reason was not extracted
    with the rest of the results, without being a fatal ReadError."""


class Task:

    """Base-class for all tasks."""
    import uuid
    id=str(uuid.uuid4())
    BASH_filename = f'ls_job_script_{id}.sh'
    job_script_first_line = "#!/bin/bash"
    remote_job_script_last_line = "touch Done"


    def __init__(self, lsconfig, 
                task_info: TaskInfo, 
                dependent_tasks: Union[List[TaskInfo],None]= None
                ) -> None:
        
        self.lsconfig = lsconfig
        self.task_info = task_info
        self.task_name = task_info.name
        self.dependent_tasks = dependent_tasks       
        self.directory = task_info.path
        # self.project_dir is deprecated and should be removed.
        self.project_dir = self.directory     
        self.engine_name = task_info.engine
        self.engine_path = self.lsconfig['engine'].get(self.engine_name , self.engine_name)
        mpi_path = self.lsconfig['mpi'].get('mpirun', 'mpirun')
        self.mpi_path = self.lsconfig['mpi'].get(f'{self.engine_name}_mpi', mpi_path)
        self.python_path = self.lsconfig['programs'].get('python', 'python')
    
    def reset_lsconfig(self, lsconfig):
        self.engine_path = lsconfig['engine'].get(self.engine_name , self.engine_name)
        mpi_path = lsconfig['mpi'].get('mpirun', 'mpirun')
        self.mpi_path = lsconfig['mpi'].get(f'{self.engine_name}_mpi', mpi_path)

    @staticmethod
    def create_directory(directory):
        absdir = os.path.abspath(directory)
        if absdir != pathlib.Path.cwd and not pathlib.Path.is_dir(directory):
            os.makedirs(directory)

    @abstractmethod
    def create_template(self):
        """This method creates engine input and stores it in the task info.
        Store the engine input in taskinfo.input['engine_input'][data] 
        filepath in taskinfo.input['engine_input']['path']"""
    
    @abstractmethod
    def write_input(self):
        """This method creates engine directory and task directory and writes 
        the engine input to a file."""        
    
    def create_input(self):
        self.task_info.state.input_created = True
        self.create_template()

    def save_input(self):
        self.task_info.state.input_saved = True
        self.write_input()

    @abstractmethod
    def prepare_input(self):
        ...
    
    def get_engine_input(self):
        return self.task_info.input['engine_input']['data']

    def set_engine_input(self, txt):
        self.task_info.input['engine_input']['data'] = txt

    def check_prerequisite(self, *_) -> bool:
        """ checks if the input files and required data files for the present task are present"""
        return True
    
    def create_job_script(self) -> list:
        """Create the bash script to run the job and "touch Done" command to it, to know when the 
        command is completed."""
        job_script = []

        job_script.append(self.job_script_first_line)
        
        return job_script

    def write_job_script(self, job_script=None):
        if job_script:
            self.job_script = job_script
        self.bash_file = self.directory / self.BASH_filename
        with open(self.bash_file, 'w+') as f:
            f.write(self.job_script)

    def add_proper_path(self, path):
        """This replaces the local paths to remote paths in the engine input."""
        engine_input = self.task_info.input.get('engine_input', None)
        if not engine_input:
            return
        template = engine_input.get('data', None)
        if not template:
            return

        if str(self.directory.parent.parent) in template:
            text = re.sub(str(self.directory.parent.parent), str(path), template)
            self.task_info.input['engine_input']['data'] = text        
            self.write_input()

    def set_submit_local(self, *args):
        self.submit_local = SubmitLocal(self, *args)

    def run_job_local(self,cmd):
        cmd = cmd + ' ' + self.BASH_filename
        self.submit_local.run_job(cmd)

    def connect_to_network(self, *args, **kwargs):
        self.submit_network = SubmitNetwork(self, *args, **kwargs)
    
    def run_job_network():
        pass
    
    def read_log(self, file):
        with open(file , 'r') as f:
            text = f.read()      
        return text
        
    def check_output(self):
        
        if hasattr(self, 'submit_network'):
            check = self.task_info.network.get('sub_returncode', None)
        else:
            check = self.task_info.local.get('returncode', None)
        if check is None:
            raise TaskFailed("Job not completed.")
        return True

def write2file(directory,filename, template) -> None:
    """Write template to a file.
    
    directroy: str
        full path of the directory to write to.
    filename: str
        name of the file with extension
    template: str
        script template which needs to be written to file.
    """

    filename = pathlib.Path(directory) / filename
    file_exists = os.access(filename, os.F_OK)
    parent_writeable = os.access(filename.parent, os.W_OK)
    file_writeable = os.access(filename, os.W_OK)
    
    if ((not file_exists and not parent_writeable) or
        (file_exists and not file_writeable)):
        msg = f'Permission denied acessing file: {filename}'
        raise PermissionError(msg)

    with open(filename, 'w+') as f:

        f.truncate()
        f.seek(0)
        f.write(template)


def assemable_job_cmd(engine_cmd:str = None, np: int =1, cd_path: str=None, 
                        mpi_path: str = None,
                        remote : bool = False,
                        scheduler_block : str = None,
                        module_load_block : str = None,
                        extra_block : str = None) -> str:
    job_script_first_line = "#!/bin/bash"
    remote_job_script_last_line = "touch Done"
    
    job_script = [job_script_first_line]
    
    if remote:
        if scheduler_block:
            job_script.append(scheduler_block)
        if module_load_block:
            job_script.append(module_load_block)

    if cd_path:
        job_script.append(f'cd {cd_path};')
    
    if engine_cmd:
        if np > 1:
            if not mpi_path:
                mpi_path = 'mpirun'
            job_script.append(f'{mpi_path} -np {np:d} {engine_cmd}')
        else:
            job_script.append(f"bash -c 'echo $$;  {engine_cmd}'")
            # job_script.append(engine_cmd)

    if extra_block:
        job_script.append(extra_block)

    if remote:
        job_script.append(remote_job_script_last_line)
    
    job_script = '\n'.join(job_script)
    return job_script


def pbs_job_script(name):

    head_job_script = f"""
#!/bin/bash
#PBS -N {name}
#PBS -o output.txt
#PBS -e error.txt
#PBS -l select=1:ncpus=4:mpiprocs=4
#PBS -q debug
#PBS -l walltime=00:30:00
#PBS -V
cd $PBS_O_WORKDIR
   """
    return head_job_script






  

