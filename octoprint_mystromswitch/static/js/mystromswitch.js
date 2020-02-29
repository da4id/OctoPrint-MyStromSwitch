$(function() {
    function mystromswitchViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.printer = parameters[2];

        self.onOffButtonEnabled = ko.observable();
        self.showShutdownOctopiOption = ko.observable();
        self.showPowerOffPrintFinishOption = ko.observable();
        self.mystromswitchPowerValue = document.getElementById("mystromswitchPowerValue")
        self.mystromswitchEnergyValue = document.getElementById("mystromswitchEnergyValue")

        self.onToggleRelayEvent = function(){
            $.ajax({
                url: API_BASEURL + "plugin/mystromswitch",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "toggleRelais",
                }),
                contentType: "application/json; charset=UTF-8"
            })
        }

        //self.onmystromswitchEvent = function() {

        //}

        //self.onOffButtonEnabled.subscribe(self.onmystromswitchEvent, self);

        self.onAutomaticShutdownEnabledChanged = function(){
            var cmd = "disableShutdownAfterFinish";
            if (self.automaticShutdownEnabled()) {
                var cmd = "enableShutdownAfterFinish";
            }
            $.ajax({
                url: API_BASEURL + "plugin/mystromswitch",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: cmd
                }),
                contentType: "application/json; charset=UTF-8"
            })
        }

        self.onAutomaticPowerOffEnabledChanged = function(){
            var cmd = "disablePowerOffAfterFinish";
            if (self.automaticShutdownEnabled()) {
                var cmd = "enablePowerOffAfterFinish";
            }
            $.ajax({
                url: API_BASEURL + "plugin/mystromswitch",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: cmd
                }),
                contentType: "application/json; charset=UTF-8"
            })
        }

        self.automaticShutdownEnabled.subscribe(self.onAutomaticShutdownEnabledChanged,self);
        self.automaticPowerOffEnabled.subscribe(self.onAutomaticPowerOffEnabledChanged,self);

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "mystromswitch" && plugin != "octoprint_mystromswitch") {
                return;
            }
			self.onOffButtonEnabled(data.onOffButtonEnabled);
			self.mystromswitchEnergyValue.innerHTML = "Energy: "+data.energy.toFixed(1)+"Wh"
			if(data.relay == false){
			    self.mystromswitchPowerValue.innerHTML = "Relay is off";
			} else if (data.power != null) {
                self.mystromswitchPowerValue.innerHTML = "Power Consumption "+data.power.toFixed(1)+"W";
            }
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        mystromswitchViewModel,
        ["loginStateViewModel", "settingsViewModel", "printerStateViewModel"],
		$(".sidebar_plugin_mystromswitch").get(0)
    ]);
});
