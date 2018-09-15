/**
 * Actions configuration directive
 * Handle actions module configuration
 */
var actionsConfigDirective = function($rootScope, toast, raspiotService, actionsService, confirm, $mdDialog, $window) {

    var actionController = ['$scope', function($scope) {
        var self = this;
        self.scripts = [];
        self.uploadFile = null;

        /**
         * Cancel dialog
         */
        self.cancelDialog = function() {
            $mdDialog.cancel();
        };

        /** 
         * Open upload dialog
         */
        self.openUploadDialog = function() {
            return $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'actionsCtl',
                templateUrl: 'uploadAction.directive.html',
                parent: angular.element(document.body),
                clickOutsideToClose: false,
                fullscreen: true
            }); 
        }; 

        /**
         * Open add dialog
         */
        self.openAddDialog = function() {
            var dial = $mdDialog.prompt()
                .title('New action name')
                .textContent('Give a name to your action script')
                .placeholder('Name')
                .ariaLabel('Name')
                .initialValue('')
                //.targetEvent(ev)
                .ok('Create new action')
                .cancel('Cancel');

            var script = null;

            $mdDialog.show(dial)
                .then(function(newScript) {
                    //check script name
                    if( !newScript.endsWith('.py') )
                    {
                        newScript += '.py';
                    }

                    //save new script
                    script = newScript;
                    return actionsService.saveScript(script, 'manual', '', '');
                })
                .then(function() {
                    //reload scripts list
                    return raspiotService.reloadModuleConfig('actions');
                })
                .then(function() {
                    //edit new script
                    $window.location.href = '#!/module/actions/edit/' + script;
                });
        };

        /**
         * Delete script
         */
        self.openDeleteDialog = function(script) {
            confirm.open('Delete script?', null, 'Delete')
                .then(function() {
                    return actionsService.deleteScript(script);
                })
                .then(function() {
                    return raspiotService.reloadModuleConfig('actions');
                })
                .then(function(config) {
                    self.scripts = config.scripts;
                    toast.success('Script deleted');
                });
        };

        /**
         * Watch upload variable to trigger upload
         */
        $scope.$watch(function() {
            return self.uploadFile;
        }, function(file) {
            if( file )
            {
                //launch upload
                toast.loading('Uploading script...');
                actionsService.uploadScript(file)
                    .then(function(resp) {
                        return raspiotService.reloadModuleConfig('actions');
                    })
                    .then(function(config) {
                        $mdDialog.hide();
                        self.scripts = config.scripts;
                        toast.success('Script uploaded');
                    });
            }
        });

        /**
         * Disable/enable specified script
         */
        self.disableScript = function(script, disabled) {
            actionsService.disableScript(script, disabled)
                .then(function(resp) {
                    return raspiotService.reloadModuleConfig('actions');
                })
                .then(function(config) {
                    self.scripts = config.scripts;

                    //message info
                    if( disabled ) {
                        toast.success('Script is disabled');
                    } else {
                        toast.success('Script is enabled');
                    }
                });
        };

        /**
         * Download script
         */
        self.downloadScript = function(script) {
            actionsService.downloadScript(script);
        };

        /**
         * Init controller
         */
        self.init = function() {
            raspiotService.getModuleConfig('actions')
                .then(function(config) {
                    self.scripts = config.scripts;
                });

            //add module actions to fabButton
            var actions = [{
                icon: 'plus',
                callback: self.openAddDialog,
                tooltip: 'Create script'
            }, {
                icon: 'upload',
                callback: self.openUploadDialog,
                tooltip: 'Upload script'
            }]; 
            $rootScope.$broadcast('enableFab', actions);
        };

    }];

    var actionLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'actions.directive.html',
        replace: true,
        controller: actionController,
        controllerAs: 'actionsCtl',
        link: actionLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('actionsConfigDirective', ['$rootScope', 'toastService', 'raspiotService', 'actionsService', 'confirmService', '$mdDialog', '$window', actionsConfigDirective]);

