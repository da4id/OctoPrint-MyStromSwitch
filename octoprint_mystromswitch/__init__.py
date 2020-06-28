# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import requests
import ssl
import time
from octoprint.events import eventManager, Events
from octoprint.util import RepeatedTimer


class MyStromSwitchPlugin(octoprint.plugin.SettingsPlugin,
                          octoprint.plugin.AssetPlugin,
                          octoprint.plugin.TemplatePlugin,
                          octoprint.plugin.StartupPlugin,
                          octoprint.plugin.EventHandlerPlugin,
                          octoprint.plugin.SimpleApiPlugin,
                          octoprint.plugin.ShutdownPlugin):

    def __init__(self):
        self.ip = None
        self.intervall = 1
        self.onOffButtonEnabled = False
        self.powerOnOnStart = False
        self.powerOffOnShutdown = False
        self.powerOffDelay = 0
        self.showShutdownOctopiOption = False
        self.showPowerOffPrintFinishOption = False
        self.shutdownDelay = 60
        self.shutdownAfterPrintFinished = False
        self.powerOffAfterPrintFinished = False

        self._status_timer = None
        self._abort_timer = None
        self._wait_for_timelapse_timer = None

        self.energy = 0
        self.lastTimeStamp = 0

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

        self.showShutdownOctopiOption = self._settings.get_boolean(["showShutdownOctopiOption"])
        self._logger.debug("showShutdownOctopiOption: %s" % self.showShutdownOctopiOption)

        self.showPowerOffPrintFinishOption = self._settings.get_boolean(["showPowerOffPrintFinishOption"])
        self._logger.debug("showPowerOffPrintFinishOption: %s" % self.showPowerOffPrintFinishOption)

        self.shutdownDelay = self._settings.get_int(["shutdownDelay"])
        self._logger.debug("shutdownDelay: %s" % self.shutdownDelay)

        self._status_timer_start()

    def get_assets(self):
        return dict(js=["js/mystromswitch.js"], css=["css/mystromswitch.css"])

    def get_template_configs(self):
        return [dict(type="sidebar",
                     name="MyStrom Switch",
                     custom_bindings=False,
                     icon="power-off"),
                dict(type="settings", custom_bindings=False)]

    def _shutdown_timer_start(self):
        if self._abort_timer is not None:
            return

        if self._wait_for_timelapse_timer is not None:
            self._wait_for_timelapse_timer.cancel()

        self._logger.info("Starting abort shutdown timer.")

        self._timeout_value = self.shutdownDelay
        self._abort_timer = RepeatedTimer(1, self._shutdown_timer_task)
        self._abort_timer.start()

    def _shutdown_timer_task(self):
        if self._timeout_value is None:
            return

        self._timeout_value -= 1
        if self._timeout_value <= 0:
            if self._wait_for_timelapse_timer is not None:
                self._wait_for_timelapse_timer.cancel()
                self._wait_for_timelapse_timer = None
            if self._abort_timer is not None:
                self._abort_timer.cancel()
                self._abort_timer = None
            if self.shutdownAfterPrintFinished:
                self._shutdown_system()
            elif self.powerOffAfterPrintFinished:
                self._setRelaisState(False)

    def _status_timer_start(self):
        if self._status_timer is not None:
            self._status_timer.cancel()
            self._logger.info("Canceling Timer")

        if self.intervall >= 1 and self.ip is not None:
            self._logger.info("Starting timer")
            self._status_timer = RepeatedTimer(self.intervall, self._status_timer_task)
            self._status_timer.start()

    def _shutdown_system(self):
        self._powerCycleRelais(False, self.powerOffDelay)
        if self.shutdownAfterPrintFinished:
            shutdown_command = self._settings.global_get(["server", "commands", "systemShutdownCommand"])
            self._logger.info("Shutting down system with command: {command}".format(command=shutdown_command))
            try:
                import sarge
                p = sarge.run(shutdown_command, async=True)
            except Exception as e:
                self._logger.exception("Error when shutting down: {error}".format(error=e))
                return

    def _status_timer_task(self):
        if self.ip is not None:
            try:
                try:
                    request = requests.get(
                        'http://{}/report'.format(self.ip), timeout=1)
                    if request.status_code == 200:
                        timestamp = time.time()
                        data = request.json()
                        if not self.lastTimeStamp == 0:
                            intervall = timestamp - self.lastTimeStamp
                            # Energy in Wh
                            self.energy = self.energy + (intervall * data["power"] / 3600)
                            self._logger.debug(
                                "Energy: " + str(self.energy) + " interval: " + str(intervall) + " power: " + str(
                                    data["power"]))
                        self.lastTimeStamp = timestamp
                        data["energy"] = self.energy
                        data["onOffButtonEnabled"] = self.onOffButtonEnabled
                        data["showShutdownOctopiOption"] = self.showShutdownOctopiOption
                        data["showPowerOffPrintFinishOption"] = self.showPowerOffPrintFinishOption
                        data["automaticShutdownEnabled"] = self.shutdownAfterPrintFinished
                        data["automaticPowerOffEnabled"] = self.powerOffAfterPrintFinished
                        self._plugin_manager.send_plugin_message(self._identifier, data)
                        return
                except (requests.exceptions.ConnectionError, ValueError) as e:
                    self._logger.exception(e)
            except Exception as exp:
                self._logger.exception(exp)
        else:
            self._logger.info("Ip is None")
        data = {"relay": True, "energy": 0, "onOffButtonEnabled": False, "showShutdownOctopiOption": False,
                "showPowerOffPrintFinishOption": False, "automaticShutdownEnabled": self.shutdownAfterPrintFinished,
                "v": self.powerOffAfterPrintFinished}
        self._plugin_manager.send_plugin_message(self._identifier, data)

    def _setRelaisState(self, newState):
        nbRetry = 0
        value = '0'
        if newState:
            value = '1'
        while nbRetry < 3:
            try:
                request = requests.get(
                    'http://{}/relay'.format(self.ip), params={'state': value}, timeout=1)
                if request.status_code == 200:
                    return
                else:
                    self._logger.info(
                        "Could not set new Relais State, Http Status Code: {}".format(request.status_code))
            except requests.exceptions.ConnectionError:
                self._logger.info("Error during set Relais state")
            nbRetry = nbRetry + 1

    # Sets the switch to a specific inverse newState,
    # waits for a specified amount of time (max 3h),
    # then sets the the switch to the newState.
    def _powerCycleRelais(self, newState, time):
        nbRetry = 0
        value = 'on'
        if newState:
            value = 'off'
        while nbRetry < 3:
            try:
                try:
                    self._logger.info("try to send Powercycle Request")
                    self._logger.info('http://{}/timer'.format(self.ip))
                    request = requests.post(
                        'http://{}/timer'.format(self.ip), params={'mode': value, 'time': time}, timeout=1)
                    if request.status_code == 200:
                        return
                    else:
                        self._logger.info(
                            "Could not powerCycle Relais, Http Status Code: {}".format(request.status_code))
                except requests.exceptions.ConnectionError as e:
                    self._logger.exception(e)
                    self._logger.info("Error during powerCycle Relais: " + str(e.message))
            except Exception as exp:
                self._logger.exception(exp)
            nbRetry = nbRetry + 1

    def _toggleRelay(self):
        nbRetry = 0
        while nbRetry < 3:
            try:
                request = requests.get(
                    'http://{}/toggle'.format(self.ip), timeout=1)
                if request.status_code == 200:
                    return
                else:
                    self._logger.info("Could not toggle Relay State, Http Status Code: {}".format(request.status_code))
            except requests.exceptions.ConnectionError:
                self._logger.info("Error during toggle Relais state")
            nbRetry = nbRetry + 1

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
        elif command == "enableShutdownAfterFinish":
            self._logger.info("enableShutdownAfterFinish")
            self.shutdownAfterPrintFinished = True
        elif command == "disableShutdownAfterFinish":
            self._logger.info("disableShutdownAfterFinish")
            self.shutdownAfterPrintFinished = False
        elif command == "enablePowerOffAfterFinish":
            self._logger.info("enablePowerOffAfterFinish")
            self.powerOffAfterPrintFinished = True
        elif command == "disablePowerOffAfterFinish":
            self._logger.info("disablePowerOffAfterFinish")
            self.powerOffAfterPrintFinished = False

    def get_api_commands(self):
        return dict(
            enableRelais=[],
            disableRelais=[],
            toggleRelais=[],
            disableShutdownAfterFinish=[],
            enableShutdownAfterFinish=[],
            disablePowerOffAfterFinish=[],
            enablePowerOffAfterFinish=[]
        )

    def on_after_startup(self):
        if self.powerOnOnStart:
            self._logger.info("Turn on Relais on Start")
            self._setRelaisState(True)

    def on_shutdown(self):
        self._logger.info("on_shutdown_event")
        if self.powerOffOnShutdown:
            if self.powerOffDelay <= 0:
                self._logger.info("Turn off Relais on Shutdown")
                self._setRelaisState(False)
            else:
                self._logger.info("Turn off Relais on Shutdown Delayed")
                self._powerCycleRelais(False, self.powerOffDelay)

    def on_settings_migrate(self, target, current):
        if target > current:
            if current <= 1:
                self.onOffButtonEnabled = False
            if current <= 2:
                self.powerOnOnStart = False,
                self.powerOffOnShutdown = False,
                self.powerOffDelay = 0
            if current <= 3:
                self.showShutdownOctopiOption = False
                self.showPowerOffPrintFinishOption = False
                self.shutdownDelay = 60

    def get_settings_version(self):
        return 4

    def get_settings_defaults(self):
        return dict(
            ip=None,
            intervall=1,
            onOffButtonEnabled=False,
            powerOnOnStart=False,
            powerOffOnShutdown=False,
            powerOffDelay=0,
            showShutdownOctopiOption=False,
            showPowerOffPrintFinishOption=False,
            shutdownDelay=60
        )

    def get_settings_restricted_paths(self):
        return dict(admin=[
            ['ip']
        ])

    def on_settings_save(self, data):
        self._logger.info("on_settings_save")
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.initialize()

    def on_event(self, event, payload):

        if not self.shutdownAfterPrintFinished and not self.powerOffAfterPrintFinished:
            return

        if not self._settings.global_get(["server", "commands", "systemShutdownCommand"]):
            self._logger.warning("systemShutdownCommand is not defined. Aborting shutdown...")
            return

        if event not in [Events.PRINT_DONE, Events.PRINT_FAILED]:
            return

        if event == Events.PRINT_FAILED and not self._printer.is_closed_or_error():
            # Cancelled job
            return

        if event in [Events.PRINT_DONE, Events.PRINT_FAILED]:
            webcam_config = self._settings.global_get(["webcam", "timelapse"], merged=True)
            timelapse_type = webcam_config["type"]
            if (timelapse_type is not None and timelapse_type != "off"):
                self._wait_for_timelapse_start()
            else:
                self._shutdown_timer_start()
            return

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
