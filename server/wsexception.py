# coding=utf-8

"""

Copyright(c) 2022 Max Qian  <astroair.cn>

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Library General Public
License version 3 as published by the Free Software Foundation.
This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Library General Public License for more details.
You should have received a copy of the GNU Library General Public License
along with this library; see the file COPYING.LIB.  If not, write to
the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
Boston, MA 02110-1301, USA.

"""

from enum import Enum

from gettext import gettext
_ = gettext

class WSCameraError(Enum):
    """
        Regular websocket camera error
    """
    ConnectError = _("Failed to connect to the camera")
    CoolingError = _("Failed to set the cooling temperature and power")

    NotSupportCooling = _("")
    NotSupportTemperatureControl = _("Camera does not support temperature control")

class WSCameraSuccess(Enum):
    """
        Regular websocket camera success
    """
    ConnectSuccess = _("Connected to the camera successfully")
    CoolingSuccess = _("Set cooling temperature and power successfully")

class WSCameraWarning(Enum):
    """
        Regular websocket camera warning
    """

class WebAppSuccess(Enum):
    """
        Regular web app success
    """
    DeviceStartedSuccess = _("Started a device server successfully")
    DeviceStoppedSuccess = _("Stopped a device server successfully")

class WebAppError(Enum):
    """
        Regular web app error
    """
    ConfigFileNotFound = _("Could not find configration file ")
    ConfigFolderNotFound = _("Could not find configration folder ")
    ScriptNotFound = _("Could not find script file ")

    EmptyConfigFile = _("Config file is empty ")

    InvalidFile = _("Invalid device configuration file {}")
    InvalidScriptPath = _("Invalid script path ")
    InvalidDeviceType = _("Invalid device type ")
    InvalidDeviceID = _("Invalid device ID")

    LoadConfigFailed = _("Could not load configuration file {}")
    LoadScriptFailed = _("Could not load script file {}")

    HadAlreadyStarted = _("This server has already contained a device ")
    HadAlreadyStartedSame = _("This server has already contained the same device you want to start now ")
    DeviceNotStarted = _("The device you are trying to stop is not available on this server")
    DeviceStopFailed = _("Failed to stop the device")

class WebAppWarning(Enum):
    """
        Regular web app warning
    """
