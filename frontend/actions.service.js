/**
 * Actions service
 * Handle action module requests
 */
var actionsService = function($q, $rootScope, rpcService) {
    var self = this;
    
    /**
     * Delete script
     */
    self.deleteScript = function(script) {
        return rpcService.sendCommand('delete_script', 'actions', {'script':script});
    };

    /**
     * Disable script
     */
    self.disableScript = function(script, disabled) {
        return rpcService.sendCommand('disable_script', 'actions', {'script':script, 'disabled':disabled});
    };

    /**
     * Download script
     */
    self.downloadScript = function(script) {
        rpcService.download('download_script', 'actions', {'script': script});
    };

    /**
     * Upload script
     */
    self.uploadScript = function(file) {
        return rpcService.upload('add_script', 'actions', file);
    };

    /**
     * Load script
     */
    self.getScript = function(script) {
        return rpcService.sendCommand('get_script', 'actions', {'script':script});
    };

    /**
     * Save script
     */
    self.saveScript = function(script, editor, header, code) {
        return rpcService.sendCommand('save_script', 'actions', {'script':script, 'editor':editor, 'header':header, 'code':code});
    };

    /**
     * Debug script
     */
    self.debugScript = function(script, eventName, eventValues) {
        return rpcService.sendCommand('debug_script', 'actions', {'script':script, 'event_name':eventName, 'event_values':eventValues});
    };

    /**
     * Rename script
     */
    self.renameScript = function(oldScript, newScript) {
        return rpcService.sendCommand('rename_script', 'actions', {'old_script':oldScript, 'new_script':newScript});
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('actionsService', ['$q', '$rootScope', 'rpcService', actionsService]);

