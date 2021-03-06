#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
from raspiot.utils import MessageRequest, MessageResponse, NoResponse, InvalidModule
from threading import Thread
from collections import deque
import time
import traceback

class ActionDebugLogger():
    """
    Logger instance for action debugging
    """

    def __init__(self, bus_push):
        """
        Constructor
        
        Args:
            bus_push (function) callback to bus push function
        """
        self.__bus_push = bus_push

    def __add_message(self, message, level):
        """
        Emit debug message event.

        Args:
            message (string): message
            level (string): log level
        """
        #push message
        request = MessageRequest()
        request.event = u'actions.debug.message'
        request.params = {
            u'message': message,
            u'level': level.upper(),
            u'timestamp': int(time.time())
        }

        #push message
        resp = None
        try:
            resp = self.__bus_push(request)
        except:
            pass

    def debug(self, message):
        """
        Info message

        Args:
            message (string): message
        """
        self.__add_message(message, u'DEBUG')

    def info(self, message):
        """
        Info message

        Args:
            message (string): message
        """
        self.__add_message(message, u'INFO')

    def warning(self, message):
        """
        Warning message

        Args:
            message (string): message
        """
        self.__add_message(message, u'WARNING')

    def warn(self, message):
        """
        Warning message

        Args:
            message (string): message
        """
        self.__add_message(message, u'WARNING')

    def error(self, message):
        """
        Error message

        Args:
            message (string): message
        """
        self.__add_message(message, u'ERROR')

    def fatal(self, message):
        """
        Critical message

        Args:
            message (string): message
        """
        self.__add_message(message, u'CRITICAL')

    def critical(self, message):
        """
        Critical message

        Args:
            message (string): message
        """
        self.__add_message(message, u'CRITICAL')

    def exception(self, message):
        """
        Handle exception message
        """
        lines = traceback.format_exc().split(u'\n')
        self.__add_message(message, u'EXCEPTION')
        for line in lines:
            if len(line.strip())>0:
                self.__add_message(line, u'EXCEPTION')




class Action(Thread):
    """
    Action class launches isolated thread for an action
    It handles 2 kinds of process:
     - if debug parameter is True, Action instance runs action once and allows you to get output traces
     - if debug parameter is False, Action instance runs undefinitely (until end of raspiot)
    """

    def __init__(self, script, bus_push, disabled, debug=False, debug_event=None):
        """
        Constructor

        Args:
            script (string): full script path
            bus_push (callback): bus push function
            disabled (bool): script disabled status
            debug (bool): set to True to execute this script once
            debug_event (MessageRequest): event that trigger script
        """
        #init
        Thread.__init__(self)
        self.logger = logging.getLogger(os.path.basename(script))

        #members
        self.__debug = debug
        if debug:
            self.__debug_logger = ActionDebugLogger(bus_push)
        self.script = script
        self.__bus_push = bus_push
        self.__events = deque()
        self.__continu = True
        self.__disabled = disabled
        self.last_execution = None
        self.error_occured = False
        self.logger_level = logging.INFO

    def stop(self):
        """
        Stop script execution
        """
        self.__continu = False

    def get_execution_status(self):
        """
        Get last execution status

        Returns:
            dict: execution status::

            {
                timestamp (str): last execution time
                error (bool): True if last execution failed
            }

        """
        return {
            u'timestamp': self.last_execution,
            u'error': self.error_occured,
        }

    def set_debug_level(self, level):
        """
        Set debug level

        Args:
            level (int): use logging.<INFO|ERROR|WARN|DEBUG>
        """
        self.logger_level = level

    def set_disabled(self, disabled):
        """
        Disable/enable script

        Args:
            disabled (bool): True to disable script exection
        """
        self.__disabled = disabled

    def is_disabled(self):
        """
        Return disabled status

        Returns:
            bool: True if script execution disabled
        """
        return self.__disabled

    def push_event(self, event):
        """
        Event received

        Args:
            event (MessageRequest): message instance
        """
        self.__events.appendleft(event)

    def run(self):
        """
        Action execution process
        """
        #configure logger
        self.logger.setLevel(self.logger_level)
        self.logger.debug(u'Action thread started')

        #check if variable is defined
        def var_defined(variable_name):
            return variable_name in vars()

        #send command helper
        def command(command, to, params=None):
            request = MessageRequest()
            request.command = command
            request.to = to
            request.params = params

            #push message
            resp = MessageResponse()
            try:
                resp = self.__bus_push(request)
            except InvalidModule:
                raise Exception(u'Module "%" does not exit (loaded?)' % to)
            except NoResponse:
                #handle long response
                raise Exception(u'No response from "%s" module' % to)

            if resp!=None and isinstance(resp, MessageResponse):
                return resp.to_dict()
            else:
                return resp

        if self.__debug:
            #event in queue, get event
            self.logger.debug(u'Action execution')

            #special logger for debug to store trace
            logger = self.__debug_logger

            #and execute file
            try:
                execfile(self.script)
            except:
                logger.exception(u'Fatal error in action "%s"' % self.script)

            #send end event
            request = MessageRequest()
            request.event = u'actions.debug.end'
            resp = self.__bus_push(request)

        else:
            #logger helper
            logger = self.logger

            #loop forever
            while self.__continu:
                if len(self.__events)>0:
                    #check if file exists
                    if not os.path.exists(self.script):
                        self.logger.error(u'Action script "%s" does not exist. Stop thread' % self.script)
                        break

                    #event in queue, process it
                    current_event = self.__events.pop()

                    #drop script execution if script disabled
                    if self.__disabled:
                        #script is disabled
                        self.logger.debug(u'Action script "%s" is disabled. Drop execution' % self.script)
                        continue

                    #event helpers
                    event = current_event[u'event']
                    event_values = current_event[u'params']
                    
                    #and execute file
                    self.logger.debug(u'Action execution')
                    try:
                        execfile(self.script)
                        self.last_execution = int(time.time())
                        self.error_occured = False
                    except:
                        self.error_occured = True
                        self.logger.exception(u'Fatal error in action script "%s"' % self.script)

                else:
                    #no event, pause
                    time.sleep(0.50)

        self.logger.debug(u'Action thread is stopped')

        
