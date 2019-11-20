$(function() {
    function mystromswitchViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.printer = parameters[2];

        self.mystromswitchEnabled = ko.observable();
        self.mystromswitchPowerValue = document.getElementById("mystromswitchPowerValue")

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
                if (data.power != null) {
                    self.mystromswitchPowerValue.innerHTML = "Power Consumption "+data.power.toFixed(2)+"W"
                }
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        mystromswitchViewModel,
        ["loginStateViewModel", "settingsViewModel", "printerStateViewModel"],
		$(".sidebar_plugin_mystromswitch").get(0)
    ]);
});
