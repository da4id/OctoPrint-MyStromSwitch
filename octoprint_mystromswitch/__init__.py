# coding=utf-8
from __future__ import absolute_import

import ssl

import octoprint.plugin
from octoprint.util import RepeatedTimer


class MyStromSwitchPlugin(octoprint.plugin.SettingsPlugin,
                          octoprint.plugin.AssetPlugin,
                          octoprint.plugin.TemplatePlugin,
                          octoprint.plugin.StartupPlugin):

    def __init__(self):
        self._pollTimer = None
        self.ip = None
        self.intervall = 1

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def initialize(self):
        self.ip = self._settings.get(["ip"])
        self._logger.debug("ip: %s" % self.ip)

        self.intervall = self._settings.get_int(["intervall"])
        self._logger.debug("intervall: %s" % self.intervall)

    def get_assets(self):
        return dict(js=["js/mystromswitch.js"], css=["css/mystromswitch.css"])

    def get_template_configs(self):
        return [dict(type="sidebar",
                     name="MyStrom Switch",
                     custom_bindings=False,
                     icon="power-off"),
                dict(type="settings", custom_bindings=False)]

    def _temperature_target(self):
        if self._abort_timer_temp is not None:
            return
        if self.temperatureTarget:
            self._abort_timer_temp = RepeatedTimer(2, self._temperature_task)
            self._abort_timer_temp.start()
        else:
            self._timer_start()

    def _temperature_task(self):
        if self._printer.get_state_id() == "PRINTING" and self._printer.is_printing() == True:
            self._abort_timer_temp.cancel()
            self._abort_timer_temp = None
            return
        self._temp = self._printer.get_current_temperatures()
        tester = 0;
        number = 0;
        for tool in self._temp.keys():
            if not tool == "bed":
                if self._temp[tool]["actual"] <= self.temperatureValue:
                    tester += 1
                number += 1
        if tester == number:
            self._abort_timer_temp.cancel()
            self._abort_timer_temp = None
            self._timer_start()

    def _timer_start(self):
        if self._abort_timer is not None:
            return

        self._logger.info("Starting abort shutdown printer timer.")

        self._timeout_value = self.abortTimeout
        self._abort_timer = RepeatedTimer(1, self._timer_task)
        self._abort_timer.start()

    def _timer_task(self):
        if self._timeout_value is None:
            return

        self._timeout_value -= 1

        if self._printer.get_state_id() == "PRINTING" and self._printer.is_printing() == True:
            self._timeout_value = 0

            self._abort_timer.cancel()
            self._abort_timer = None
            return
        if self._timeout_value <= 0:
            if self._abort_timer is not None:
                self._abort_timer.cancel()
                self._abort_timer = None
            self._shutdown_printer()

    def on_after_startup(self):
        self._logger.info("Hello World!")

    def get_settings_defaults(self):
        return dict(
            ip="",
            intervall=1
        )

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.ip = self._settings.get(["ip"])
        self.intervall = self._settings.get_int(["intervall"])

    def get_update_information(self):
        return dict(
            mystromswitch=dict(
                displayName="OctoPrint-MyStromSwitch",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="da4id",
                repo="OctoPrint-MyStromSwitch",
                current=self._plugin_version,

                # update method: pip w/ dependency links
                pip="https://github.com/da4id/OctoPrint-MyStromSwitch/archive/{target_version}.zip"
            )
        )


__plugin_name__ = "OctoPrint-MyStromSwitch"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = MyStromSwitchPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
