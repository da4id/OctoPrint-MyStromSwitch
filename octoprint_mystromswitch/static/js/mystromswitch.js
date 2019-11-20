$(function() {
    function mystromswitchViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.printer = parameters[2];

        // Hack to remove automatically added Cancel button
        // See https://github.com/sciactive/pnotify/issues/141
        //PNotify.prototype.options.confirm.buttons = [];
		//another way use, add custom style class for hide cancel button
        self.timeoutPopupText = gettext('Shutting down printer in ');
        self.timeoutPopupOptions = {
            title: gettext('Shutdown Printer'),
            type: 'notice',
            icon: true,
            hide: false,
            confirm: {
                confirm: true,
                buttons: [{
                    text: 'Abort Shutdown Printer',
                    addClass: 'btn-block btn-danger',
                    promptTrigger: true,
                    click: function(notice, value){
                        notice.remove();
                        notice.get().trigger("pnotify.cancel", [notice, value]);
                    }
                }, {
                    addClass: 'mystromswitchHideCancelBtnConfirm',
                    promptTrigger: true,
                    click: function(notice, value){
                        notice.remove();

                    }
                }]
            },
            buttons: {
                closer: false,
                sticker: false,
            },
            history: {
                history: false
            }
        };

        //for touch ui
		self.touchUIMoveElement = function (self, counter) {
			var hash = window.location.hash;
			if (hash != "" && hash != "#printer" && hash != "#touch")
			{
				return;
			}
			if (counter < 10) {
				if (document.getElementById("touch") != null && document.getElementById("printer") != null && document.getElementById("printer") != null && document.getElementById("touch").querySelector("#printer").querySelector("#files_wrapper")) {
					var newParent = document.getElementById("files_wrapper").parentNode;
					newParent.insertBefore(document.getElementById('sidebar_plugin_mystromswitch_wrapper'), document.getElementById("files_wrapper"));
				} else {
					setTimeout(self.touchUIMoveElement, 1000, self, ++counter);
				}
			}
		}
		 //add octoprint event for check finish
		self.onStartupComplete = function () {
			//self.touchUIMoveElement(self, 0);
			if (self.printer.isPrinting())
			{
				self.testButtonChangeStatus(true);
			} else {
				self.testButtonChangeStatus(false);
			}


		};

		self.onUserLoggedIn = function() {
			$.ajax({
                    url: API_BASEURL + "plugin/mystromswitch",
                    type: "POST",
                    dataType: "json",
                    data: JSON.stringify({
                        command: "update",
						eventView : false
                    }),
                    contentType: "application/json; charset=UTF-8"
            })
			$.ajax({
				url: API_BASEURL + "plugin/mystromswitch",
				type: "POST",
				data: JSON.stringify({
					command: "status"
				}),
				context:self,
				contentType: "application/json; charset=UTF-8"
			}).done(function(data, textStatus, jqXHR ){
				this.mystromswitchEnabled(data == "True" ? true : false);
			})
		}

		self.onUserLoggedOut = function() {
		}

		self.onEventPrinterStateChanged = function(payload) {
        			if (payload.state_id == "PRINTING" || payload.state_id == "PAUSED"){
        				self.testButtonChangeStatus(true);
        			} else {
        				self.testButtonChangeStatus(false);
        			}
        		}

        self.onmystromswitchEvent = function() {
            if (self.mystromswitchEnabled()) {
                $.ajax({
                    url: API_BASEURL + "plugin/mystromswitch",
                    type: "POST",
                    dataType: "json",
                    data: JSON.stringify({
                        command: "enable",
						eventView : false
                    }),
                    contentType: "application/json; charset=UTF-8"
                })
            } else {
                $.ajax({
                    url: API_BASEURL + "plugin/mystromswitch",
                    type: "POST",
                    dataType: "json",
                    data: JSON.stringify({
                        command: "disable",
						eventView : false
                    }),
                    contentType: "application/json; charset=UTF-8"
                })
            }
        }

        self.mystromswitchEnabled.subscribe(self.onmystromswitchEvent, self);

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "mystromswitch" && plugin != "octoprint_mystromswitch") {
                return;
            }

			 self.mystromswitchEnabled(data.mystromswitchEnabled);
            if (data.type == "timeout") {
                if ((data.timeout_value != null) && (data.timeout_value > 0)) {
                    self.timeoutPopupOptions.text = self.timeoutPopupText + data.timeout_value;
                    if (typeof self.timeoutPopup != "undefined") {
                        self.timeoutPopup.update(self.timeoutPopupOptions);
                    } else {
                        self.timeoutPopup = new PNotify(self.timeoutPopupOptions);
                        self.timeoutPopup.get().on('pnotify.cancel', function() {self.abortShutdown(true);});
                    }
                } else {
                    if (typeof self.timeoutPopup != "undefined") {
                        self.timeoutPopup.remove();
                        self.timeoutPopup = undefined;
                    }
                }
            }
        }

        self.abortShutdown = function(abortShutdownValue) {
            self.timeoutPopup.remove();
            self.timeoutPopup = undefined;
            $.ajax({
                url: API_BASEURL + "plugin/mystromswitch",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "abort",
					eventView : true
                }),
                contentType: "application/json; charset=UTF-8"
            })
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        mystromswitchViewModel,
        ["loginStateViewModel", "settingsViewModel", "printerStateViewModel"],
		$(".sidebar_plugin_mystromswitch").get(0)
    ]);
});
