import os
import traceback
import Common
from robot.libraries.BuiltIn import BuiltIn

class Extra():
    """ Handles extra work
    """
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'
    
    def __init__(self):
        try:
            # load extra libraries
            for lib in Common.GLOBAL['extra-lib']:
		lib_name = lib + '.py'
                BuiltIn().import_library(os.environ['RENAT_PATH'] + '/'+ lib_name)
                BuiltIn().log_to_console("Loaded extra library `%s`" % lib)
        
        except Exception as e:
            # raise Exception("Error while loading extra libraries")
            Common.err("Error while loading extra libraries")
            Common.err(e)

    def connect_all(self):
        for lib in Common.GLOBAL['extra-lib']:
            BuiltIn().run_keyword(lib+'.Connect All')
    
    def close_all(self):
        for lib in Common.GLOBAL['extra-lib']:
            BuiltIn().run_keyword(lib+'.Close All')
    
    def test(self): 
        pass
