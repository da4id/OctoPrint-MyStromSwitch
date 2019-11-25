# coding=utf-8
from __future__ import absolute_import

import ssl

import octoprint.plugin
import requests
from octoprint.util import RepeatedTimer


class MyStromSwitchPlugin(octoprint.plugin.SettingsPlugin,
                          octoprint.plugin.AssetPlugin,
                          octoprint.plugin.TemplatePlugin,
                          octoprint.plugin.StartupPlugin,
                          octoprint.plugin.SimpleApiPlugin,
                          octoprint.plugin.ShutdownPlugin):

    def __init__(self):
        self.ip = None
        self.intervall = 1
        self.onOffButtonEnabled = False
        self.powerOnOnStart = False
        self.powerOffOnShutdown = False
        self.powerOffDelay = 0

        self._timer = None

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def initialize(self):
        self.ip = self._settings.get(["ip"])
        self._logger.debug("ip: %s" % self.ip)

        self.intervall = self._settings.get_int(["intervall"])
        self._logger.debug("intervall: %s" % self.intervall)

        self.onOffButtonEnabled = self._settings.get_boolean(["onOffButtonEnabled"])
        self._logger.debug("onOffButtonEnabled: %s" % self.onOffButtonEnabled)

        self.powerOnOnStart = self._settings.get_boolean(["powerOnOnStart"])
        self._logger.debug("powerOnOnStart: %s" % self.powerOnOnStart)

        self.powerOffOnShutdown = self._settings.get_boolean(["powerOffOnShutdown"])
        self._logger.debug("powerOffOnShutdown: %s" % self.powerOffOnShutdown)

        self.powerOffDelay = self._settings.get_int(["powerOffDelay"])
        self._logger.debug("powerOffDelay: %s" % self.powerOffDelay)

        self._timer_start()

    def get_assets(self):
        return dict(js=["js/mystromswitch.js"], css=["css/mystromswitch.css"])

    def get_template_configs(self):
        return [dict(type="sidebar",
                     name="MyStrom Switch",
                     custom_bindings=False,
                     icon="power-off"),
                dict(type="settings", custom_bindings=False)]

    def _timer_start(self):
        if self._timer is not None:
            self._timer.cancel()
            self._logger.info("Canceling Timer")

        if self.intervall >= 1 and self.ip is not None:
            self._logger.info("Starting timer")
            self._timer = RepeatedTimer(self.intervall, self._timer_task)
            self._timer.start()

    def _timer_task(self):
        if self.ip is not None:
            try:
                request = requests.get(
                    'http://{}/report'.format(self.ip), timeout=1)
                data = request.json()
                data["onOffButtonEnabled"] = self.onOffButtonEnabled
                self._plugin_manager.send_plugin_message(self._identifier, data)
            except (requests.exceptions.ConnectionError, ValueError):
                self._logger.info('Connection Error Host: {}'.format(self.ip))
        else:
            self._logger.info("Ip is None")

    def _setRelaisState(self, newState):
        try:
            value = '0'
            if (newState == True):
                value = '1'
            request = requests.get(
                'http://{}/relay'.format(self.ip), params={'state': value}, timeout=1)
            if not request.status_code == 200:
                self._logger.info("Could not set new Relais State, Http Status Code: {}".format(request.status_code))
        except requests.exceptions.ConnectionError:
            self._logger.info("Error during set Relais state")

    # Sets the switch to a specific inverse newState,
    # waits for a specified amount of time (max 3h),
    # then sets the the switch to the newState.
    def _powerCycleRelais(self, newState, time):
        try:
            value = 'on'
            if (newState == True):
                value = 'off'
            request = requests.post(
                'http://{}/timer'.format(self.ip), params={'mode': value, 'time': time}, timeout=1)
            if not request.status_code == 200:
                self._logger.info("Could not powerCycle Relais, Http Status Code: {}".format(request.status_code))
        except requests.exceptions.ConnectionError:
            self._logger.info("Error during powerCycle Relais")

    def _toggleRelay(self):
        try:
            request = requests.get(
                'http://{}/toggle'.format(self.ip), timeout=1)
            if not request.status_code == 200:
                self._logger.info("Could not toggle Relay State, Http Status Code: {}".format(request.status_code))
        except requests.exceptions.ConnectionError:
            self._logger.info("Error during toggle Relais state")

    def on_api_command(self, command, data):
        if command == "enableRelais":
            self._logger.info("enableRelais")
            self._setRelaisState(True)
        elif command == "disableRelais":
            self._logger.info("disableRelais")
            self._setRelaisState(False)
        elif command == "toggleRelais":
            self._logger.info("toggleRelais")
            self._toggleRelay()

    def get_api_commands(self):
        return dict(
            enableRelais=[],
            disableRelais=[],
            toggleRelais=[]
        )

    def on_after_startup(self):
        if self.powerOnOnStart:
            self._logger.info("Turn on Relais on Start")
            self._setRelaisState(True)

    def on_shutdown(self):
        if self.powerOffOnShutdown:
            if self.powerOffDelay <= 0:
                self._logger.info("Turn on Relais off Shutdown")
                self._setRelaisState(False)
            else:
                self._logger.info("Turn off Relais on Shutdown Delayed")
                self._powerCycleRelais(False, self.powerOffDelay)

    def on_settings_migrate(self, target, current):
        if target > current:
            if current <= 1:
                self.onOffButtonEnabled = False
                pass
            if current <= 2:
                self.powerOnOnStart = False,
                self.powerOffOnShutdown = False,
                self.powerOffDelay = 0

    def get_settings_version(self):
        return 3

    def get_settings_defaults(self):
        return dict(
            ip=None,
            intervall=1,
            onOffButtonEnabled=False,
            owerOnOnStart=False,
            powerOffOnShutdown=False,
            powerOffDelay=0
        )

    def on_settings_save(self, data):
        self._logger.info("on_settings_save")
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.initialize()

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


__plugin_name__ = "MyStrom Switch"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = MyStromSwitchPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
