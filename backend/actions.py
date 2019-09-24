#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.utils import InvalidParameter, CommandError
from raspiot.raspiot import RaspIotModule
from threading import Lock
import time
import re
from raspiot.libs.internals.task import Task
from script import Script

__all__ = ['Actions']

class Actions(RaspIotModule):
    """
    Action allows user to execute its own python scripts interacting with RaspIot
    """

    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_CATEGORY = u'APPLICATION'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Interact with other modules to trigger custom actions'
    MODULE_LONGDESCRIPTION = u"""Write your own python script as Cleep actions.<br>
                                Those actions can interact with all installed modules and trigger custom actions according to received events.<br>
                                Action scripts are written in Python and executed after any event is received. This application is the best place
                                to quickly implement cron job for example."""
    MODULE_TAGS = [u'action', u'skill', u'script', u'trigger', u'python', u'cron']
    MODULE_COUNTRY = None
    MODULE_URLINFO = u'https://github.com/tangb/cleepmod-actions'
    MODULE_URLHELP = u'https://github.com/tangb/cleepmod-actions/wiki'
    MODULE_URLBUGS = u'https://github.com/tangb/cleepmod-actions/issues'
    MODULE_URLSITE = None

    MODULE_CONFIG_FILE = u'actions.conf'

    SCRIPTS_PATH = u'/var/opt/raspiot/scripts'
    DEFAULT_CONFIG = {
        u'scripts': {}
    }

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        #init
        RaspIotModule.__init__(self, bootstrap, debug_enabled)

        #make sure sounds path exists
        if not os.path.exists(Actions.SCRIPTS_PATH):
            self.cleep_filesystem.mkdir(Actions.SCRIPTS_PATH, True)

        #init members
        self.__scripts = {}
        self.__load_scripts_lock = Lock()

    def _configure(self):
        """
        Configure module
        """
        #launch scripts threads
        self.__load_scripts()

        #refresh scripts task
        self.__refresh_thread = Task(60.0, self.__load_scripts, self.logger)
        self.__refresh_thread.start()

    def _stop(self):
        """
        Stop module
        """
        #stop refresh thread
        self.__refresh_thread.stop()

        #stop all scripts
        for script in self.__scripts:
            self.__scripts[script].stop()

    def __load_scripts(self):
        """
        Launch dedicated thread for each script found
        """
        self.__load_scripts_lock.acquire()

        #remove stopped threads (script was removed?)
        scripts = self._get_config_field(u'scripts')
        for script in self.__scripts.keys():
            #check file existance
            if not os.path.exists(os.path.join(Actions.SCRIPTS_PATH, script)):
                #file doesn't exist from filesystem, clear config entry
                self.logger.info(u'Delete infos from removed script "%s"' % script)

                if script in self.__scripts:
                    #stop running thread if necessary
                    if self.__scripts[script].is_alive():
                        self.__scripts[script].stop()

                    #clear config entry
                    del self.__scripts[script]
                    if script in scripts:
                        del scripts[script]
                        self._set_config_field(u'scripts', scripts)
                    
        #launch thread for new script
        for root, dirs, scripts in os.walk(Actions.SCRIPTS_PATH):
            for script in scripts:
                #drop files that aren't python script
                ext = os.path.splitext(script)[1]
                if ext!=u'.py':
                    self.logger.debug(u'Drop bad extension file "%s"' % script)
                    continue

                scripts = self._get_config_field(u'scripts')
                if not self.__scripts.has_key(script):
                    self.logger.info(u'Discover new script "%s"' % script)
                    #get disable status
                    disabled = False
                    if script in scripts:
                        disabled = scripts[script][u'disabled']
                    else:
                        scripts[script] = {
                            u'disabled': disabled
                        }
                        self._set_config_field(u'scripts', scripts)

                    #start new thread
                    self.__scripts[script] = Script(os.path.join(root, script), self.push, disabled)
                    self.__scripts[script].start()

        self.__load_scripts_lock.release()

    def get_module_config(self):
        """
        Return full module configuration

        Returns:
            dict: module configuration
        """
        config = {}
        config[u'scripts'] = self.get_scripts()
        return config

    def event_received(self, event):
        """
        Event received

        Args:
            event (MessageRequest): an event
        """
        self.logger.debug(u'Event received %s' % unicode(event))
        #push event to all script threads
        for script in self.__scripts:
            self.__scripts[script].push_event(event)

    def get_script(self, script):
        """
        Return a script

        Params:
            script (string): script name

        Returns:
            dict: script data::
                {
                    visual (string): visual editor used to edit file or None if no editor used
                    code (string): source code
                    header (string): source file header (can contains necessary infos for visual editor)
                }

        Raises:
            InvalidParameter: if script not found
            CommandError: if error occured processing script
        """
        self.logger.debug(u'Config: %s' % self._get_config())
        if not self.__scripts.has_key(script):
            raise InvalidParameter(u'Unknown script "%s"' % script)
        path = os.path.join(Actions.SCRIPTS_PATH, script)
        if not os.path.exists(path):
            raise InvalidParameter(u'Script "%s" does not exist' % script)

        output = {
            u'visual': None,
            u'code': None,
            u'header': None
        }

        #read file content
        self.logger.debug(u'Loading script: %s' % path)
        lines = self.cleep_filesystem.read_data(path, encoding='utf-8')
        content = u'\n'.join(lines)

        #parse file
        groups = re.findall(u'# -\*- coding: utf-8 -\*-\n(?:\"\"\"\neditor:(\w+)\n(.*)\n\"\"\"\s)?(.*)', content, re.S | re.U)
        self.logger.debug(groups)
        if len(groups)==1:
            if len(groups[0])==3:
                output[u'editor'] = groups[0][0]
                output[u'header'] = groups[0][1]
                output[u'code'] = groups[0][2]
            else:
                raise CommandError(u'Unable to load script: invalid format')
        else:
            self.logger.warning(u'Unhandled source code: %s' % groups)

        return output

    def save_script(self, script, editor, header, code):
        """
        Save script content. If script name if not found, it will create new script

        Params:
            script (string): script name
            editor (string): editor name
            header (string): script header (header comments, may contains editor specific stuff)
            code (string): source code

        Returns:
            bool: True if script saved successfully

        Raises:
            MissingParameter: if parameter is missing
            CommandError: if error processing script
        """
        if script is None or len(script)==0:
            raise InvalidParameter(u'Script parameter is missing')
        if editor is None or len(editor)==0:
            raise InvalidParameter(u'editor parameter is missing')
        if header is None:
            raise InvalidParameter(u'Header parameter is missing')
        if code is None:
            raise InvalidParameter(u'Code parameter is missing')

        #open script for writing
        path = os.path.join(Actions.SCRIPTS_PATH, script)
        self.logger.debug(u'Opening script: %s' % path)
        #fd = io.open(path, u'w', encoding=u'utf-8')
        content = u'# -*- coding: utf-8 -*-\n"""\neditor:%s\n%s\n"""\n%s' % (editor, header, code)
        #fd.write(content)
        #fd.close()
        self.cleep_filesystem.write_data(path, content, encoding='utf-8')

        #force script loading
        self.__load_scripts()

    def get_scripts(self):
        """
        Return scripts
        
        Returns:
            list: list of scripts::
                [
                    {
                        name (string): script name
                        lastexecution (timestamp): last execution time
                        disabled (bool): True if script is disabled
                    },
                    ...
                ]
        """
        scripts = []
        for script in self.__scripts:
            script = {
                u'name': script,
                u'lastexecution': self.__scripts[script].get_last_execution(),
                u'disabled': self.__scripts[script].is_disabled()
            }
            scripts.append(script)

        return scripts

    def disable_script(self, script, disabled):
        """
        Enable/disable specified script
        
        Args:
            script (string): script name
            disable (bool): disable flag

        Raises:
            InvalidParameter: if parameter is invalid
        """
        if not self.__scripts.has_key(script):
            raise InvalidParameter(u'Script not found')

        #enable/disable script
        scripts = self._get_config_field(u'scripts')
        scripts[script][u'disabled'] = disabled
        self._set_config_field(u'scripts', scripts)
        self.__scripts[script].set_disabled(disabled)

    def delete_script(self, script):
        """
        Delete specified script

        Args:
            script (string): script name
        """
        for root, dirs, scripts in os.walk(Actions.SCRIPTS_PATH):
            for script_ in scripts:
                if script==script_:
                    #script found, remove from filesystem
                    os.remove(os.path.join(Actions.SCRIPTS_PATH, script))
                    #force script loading
                    self.__load_scripts()
                    return True

        return False

    def add_script(self, filepath):
        """
        Add new script using rpc upload

        Args:
            filepath (string): script full path

        Raises:
            InvalidParameter: if invalid parameter is specified
            Exception: if error occured
        """
        #check parameters
        file_ext = os.path.splitext(filepath)
        self.logger.info(u'uploaded file extension: %s - %s' % (unicode(file_ext), unicode(file_ext[1])))
        if file_ext[1]!=u'.py':
            self.logger.info(u'uploaded file extension: %s' % unicode(file_ext[1][1:]))
            raise InvalidParameter(u'Invalid script file uploaded (only python script are supported)')

        #move file to valid dir
        if os.path.exists(filepath):
            name = os.path.basename(filepath)
            path = os.path.join(Actions.SCRIPTS_PATH, name)
            self.logger.info(u'Name=%s path=%s' % (name, path))
            self.cleep_filesystem.move(filepath, path)
            self.logger.info(u'File "%s" uploaded successfully' % name)

            #reload scripts
            self.__load_scripts()

        else:
            #file doesn't exists
            self.logger.error(u'Script file "%s" doesn\'t exist' % filepath)
            raise Exception(u'Script file "%s"  doesn\'t exists' % filepath)

    def download_script(self, script):
        """
        Download specified script

        Args:
            script (string): script name to download

        Returns:
            string: script full path

        Raises:
            Exception: if error occured
        """
        filepath = os.path.join(Actions.SCRIPTS_PATH, script)
        if os.path.exists(filepath):
            #script is valid, return full filepath
            return {
                u'filepath': filepath
            }
        else:
            #script doesn't exist, raise exception
            raise Exception(u'Script "%s" doesn\'t exist' % script)

    def debug_script(self, script, event_name=None, event_values=None):
        """
        Launch script debugging. Script output will be send to message bus as event

        Params:
            script (string): script name
            event_name (string): event name
            event_values (dict): event values

        Raises:
            InvalidParameter
        """
        if not self.__scripts.has_key(script):
            raise InvalidParameter(u'Unknown script "%s"' % script)
        path = os.path.join(Actions.SCRIPTS_PATH, script)
        if not os.path.exists(path):
            raise InvalidParameter(u'Script "%s" does not exist' % script)
        
        #TODO handle event
        debug = Script(os.path.join(Actions.SCRIPTS_PATH, script), self.push, False, True)
        debug.start()

    def rename_script(self, old_script, new_script):
        """
        Rename script

        Args:
            old_script (string): old script name
            new_script (string): new script name

        Raises:
            MissingParameter, InvalidParameter
        """
        if old_script is None or len(old_script)==0:
            raise MissingParameter(u'Old_script parameter is missing')
        if new_script is None or len(new_script)==0:
            raise MissingParameter(u'New_script parameter is missing')
        if old_script==new_script:
            raise InvalidParameter(u'Script names must be differents')
        if not self.__scripts.has_key(old_script):
            raise InvalidParameter(u'Script "%s" does not exist' % old_script)
        if self.__scripts.has_key(new_script):
            raise InvalidParameter(u'Script "%s" already exists' % new_script)

        #rename script in filesystem
        self.cleep_filesystem.move(os.path.join(Actions.SCRIPTS_PATH, old_script), os.path.join(Actions.SCRIPTS_PATH, new_script))
        time.sleep(0.5)

        #rename script in config
        scripts = self._get_config_field(u'scripts')
        old = scripts[old_script]
        scripts[new_script] = old
        del scripts[old_script]
        self._set_config_field(u'scripts', scripts)

        #reload scripts
        self.__load_scripts()

        
