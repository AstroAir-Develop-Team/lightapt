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

from server.basic.camera import BasicCameraAPI,BasicCameraInfo

from utils.utility import switch
from utils.lightlog import lightlog
log = lightlog(__name__)

import gettext
_ = gettext.gettext

import ctypes
import numpy as np
import astropy.io.fits as fits
from enum import Enum
from base64 import b64encode
from datetime import datetime
from io import BytesIO
from json import dumps
from os import mkdir,path,environ,getcwd
from time import sleep

class ASI_BAYER_PATTERN(Enum):
    ASI_BAYER_RG = 0
    ASI_BAYER_BG = 1
    ASI_BAYER_GR = 2
    ASI_BAYER_RB = 3

class ASI_IMGTYPE(Enum):
    ASI_IMG_RAW8 = 0
    ASI_IMG_RGB24 = 1
    ASI_IMG_RAW16 = 2
    ASI_IMG_Y8 = 3
    ASI_IMG_END = -1

class ASI_GUIDE_DIRECTION(Enum):
    ASI_GUIDE_NORTH = 0
    ASI_GUIDE_SOUTH = 1
    ASI_GUIDE_EAST = 2
    ASI_GUIDE_WEST = 3

class ASI_CONTROL_TYPE(Enum):
    ASI_GAIN = 0
    ASI_EXPOSURE = 1
    ASI_GAMMA = 2
    ASI_WB_R = 3
    ASI_WB_B = 4
    ASI_BRIGHTNESS = 5
    ASI_OFFSET = 5
    ASI_BANDWIDTHOVERLOAD = 6
    ASI_OVERCLOCK = 7
    ASI_TEMPERATURE = 8  # return 10*temperature
    ASI_FLIP = 9
    ASI_AUTO_MAX_GAIN = 10
    ASI_AUTO_MAX_EXP = 11
    ASI_AUTO_MAX_BRIGHTNESS = 12
    ASI_HARDWARE_BIN = 13
    ASI_HIGH_SPEED_MODE = 14
    ASI_COOLER_POWER_PERC = 15
    ASI_TARGET_TEMP = 16  # not need *10
    ASI_COOLER_ON = 17
    ASI_MONO_BIN = 18  # lead to less grid at software bin mode for color camera
    ASI_FAN_ON = 19
    ASI_PATTERN_ADJUST = 20

class ASI_CAMERA_MODE(Enum):
    ASI_MODE_NORMAL = 0 
    ASI_MODE_TRIG_SOFT_EDGE = 1
    ASI_MODE_TRIG_RISE_EDGE = 2
    ASI_MODE_TRIG_FALL_EDGE = 3
    ASI_MODE_TRIG_SOFT_LEVEL = 4
    ASI_MODE_TRIG_HIGH_LEVEL = 5
    ASI_MODE_TRIG_LOW_LEVEL = 6
    ASI_MODE_END = -1

class ASI_TRIG_OUTPUT(Enum):
    ASI_TRIG_OUTPUT_PINA = 0
    ASI_TRIG_OUTPUT_PINB = 1
    ASI_TRIG_OUTPUT_NONE = -1

class ASI_EXPOSURE_STATUS(Enum):
    ASI_EXP_IDLE = 0
    ASI_EXP_WORKING = 1
    ASI_EXP_SUCCESS = 2
    ASI_EXP_FAILED = 3

class _ASI_CAMERA_INFO(ctypes.Structure):
    """ASI camera info"""
    _fields_ = [
        ('Name', ctypes.c_char * 64),
        ('CameraID', ctypes.c_int),
        ('MaxHeight', ctypes.c_long),
        ('MaxWidth', ctypes.c_long),
        ('IsColorCam', ctypes.c_int),
        ('BayerPattern', ctypes.c_int),
        ('SupportedBins', ctypes.c_int * 16),
        ('SupportedVideoFormat', ctypes.c_int * 8),
        ('PixelSize', ctypes.c_double),  # in um
        ('MechanicalShutter', ctypes.c_int),
        ('ST4Port', ctypes.c_int),
        ('IsCoolerCam', ctypes.c_int),
        ('IsUSB3Host', ctypes.c_int),
        ('IsUSB3Camera', ctypes.c_int),
        ('ElecPerADU', ctypes.c_float),
        ('BitDepth', ctypes.c_int),
        ('IsTriggerCam', ctypes.c_int),

        ('Unused', ctypes.c_char * 16)
    ]

class _ASI_CONTROL_CAPS(ctypes.Structure):
    _fields_ = [
        ('Name', ctypes.c_char * 64),
        ('Description', ctypes.c_char * 128),
        ('MaxValue', ctypes.c_long),
        ('MinValue', ctypes.c_long),
        ('DefaultValue', ctypes.c_long),
        ('IsAutoSupported', ctypes.c_int),
        ('IsWritable', ctypes.c_int),
        ('ControlType', ctypes.c_int),
        ('Unused', ctypes.c_char * 32),
        ]

class _ASI_ID(ctypes.Structure):
    _fields_ = [('id', ctypes.c_char * 8)]

class _ASI_SUPPORTED_MODE(ctypes.Structure):
    _fields_ = [('SupportedCameraMode', ctypes.c_int * 16)]

class ASICameraAPI(BasicCameraAPI):
    """
        ASI Camera API via ASICamera2.dll/so
    """

    def __init__(self) -> None:
        self.info = BasicCameraInfo()
        self.device = None
        self.info._is_connected = False
    
    def __del__(self) -> None:
        if self.info._is_connected:
            self.disconnect()

    def init_dll(self) -> None:
        """
            Initialize the dll library | 加载dll
            Args: None
            Returns: None
        """

        if self.device is not None:
            return
        _p = path.join
        libpath = _p(_p(getcwd(),"libs"),"zwoasi")
        # 判断系统位数 - 32/64
        if 'PROGRAMFILES(X86)' in environ:
            libpath = _p(_p(libpath,"x64"),"ASICamera2.dll")
        else:
            libpath = _p(_p(libpath,"x86"),"ASICamera2.dll")
        # 检查库是否存在
        if path.isfile(libpath):
            log.log(f"Find {libpath}")
        else:
            log.loge(f"Failed to find {libpath}")
        # 加载动态库
        self.device = ctypes.cdll.LoadLibrary(libpath)

        self.device.ASIGetNumOfConnectedCameras.argtypes = []
        self.device.ASIGetNumOfConnectedCameras.restype = ctypes.c_int

        self.device.ASIGetCameraProperty.argtypes = [ctypes.POINTER(_ASI_CAMERA_INFO), ctypes.c_int]
        self.device.ASIGetCameraProperty.restype = ctypes.c_int

        self.device.ASIOpenCamera.argtypes = [ctypes.c_int]
        self.device.ASIOpenCamera.restype = ctypes.c_int

        self.device.ASIInitCamera.argtypes = [ctypes.c_int]
        self.device.ASIInitCamera.restype = ctypes.c_int

        self.device.ASICloseCamera.argtypes = [ctypes.c_int]
        self.device.ASICloseCamera.restype = ctypes.c_int

        self.device.ASIGetNumOfControls.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.device.ASIGetNumOfControls.restype = ctypes.c_int

        self.device.ASIGetControlCaps.argtypes = [ctypes.c_int, ctypes.c_int,
                                            ctypes.POINTER(_ASI_CONTROL_CAPS)]
        self.device.ASIGetControlCaps.restype = ctypes.c_int

        self.device.ASIGetControlValue.argtypes = [ctypes.c_int,
                                            ctypes.c_int,
                                            ctypes.POINTER(ctypes.c_long),
                                            ctypes.POINTER(ctypes.c_int)]
        self.device.ASIGetControlValue.restype = ctypes.c_int

        self.device.ASISetControlValue.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_long, ctypes.c_int]
        self.device.ASISetControlValue.restype = ctypes.c_int

        self.device.ASIGetROIFormat.argtypes = [ctypes.c_int,
                                        ctypes.POINTER(ctypes.c_int),
                                        ctypes.POINTER(ctypes.c_int),
                                        ctypes.POINTER(ctypes.c_int),
                                        ctypes.POINTER(ctypes.c_int)]
        self.device.ASIGetROIFormat.restype = ctypes.c_int

        self.device.ASISetROIFormat.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.device.ASISetROIFormat.restype = ctypes.c_int

        self.device.ASIGetStartPos.argtypes = [ctypes.c_int,
                                        ctypes.POINTER(ctypes.c_int),
                                        ctypes.POINTER(ctypes.c_int)]
        self.device.ASIGetStartPos.restype = ctypes.c_int

        self.device.ASISetStartPos.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.device.ASISetStartPos.restype = ctypes.c_int

        self.device.ASIGetDroppedFrames.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.device.ASIGetDroppedFrames.restype = ctypes.c_int

        self.device.ASIEnableDarkSubtract.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char)]
        self.device.ASIEnableDarkSubtract.restype = ctypes.c_int

        self.device.ASIDisableDarkSubtract.argtypes = [ctypes.c_int]
        self.device.ASIDisableDarkSubtract.restype = ctypes.c_int

        self.device.ASIStartVideoCapture.argtypes = [ctypes.c_int]
        self.device.ASIStartVideoCapture.restype = ctypes.c_int

        self.device.ASIStopVideoCapture.argtypes = [ctypes.c_int]
        self.device.ASIStopVideoCapture.restype = ctypes.c_int

        self.device.ASIGetVideoData.argtypes = [ctypes.c_int,
                                        ctypes.POINTER(ctypes.c_char),
                                        ctypes.c_long,
                                        ctypes.c_int]
        self.device.ASIGetVideoData.restype = ctypes.c_int

        self.device.ASIPulseGuideOn.argtypes = [ctypes.c_int, ctypes.c_int]
        self.device.ASIPulseGuideOn.restype = ctypes.c_int

        self.device.ASIPulseGuideOff.argtypes = [ctypes.c_int, ctypes.c_int]
        self.device.ASIPulseGuideOff.restype = ctypes.c_int

        self.device.ASIStartExposure.argtypes = [ctypes.c_int, ctypes.c_int]
        self.device.ASIStartExposure.restype = ctypes.c_int

        self.device.ASIStopExposure.argtypes = [ctypes.c_int]
        self.device.ASIStopExposure.restype = ctypes.c_int

        self.device.ASIGetExpStatus.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.device.ASIGetExpStatus.restype = ctypes.c_int

        self.device.ASIGetDataAfterExp.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char), ctypes.c_long]
        self.device.ASIGetDataAfterExp.restype = ctypes.c_int

        self.device.ASIGetID.argtypes = [ctypes.c_int, ctypes.POINTER(_ASI_ID)]
        self.device.ASIGetID.restype = ctypes.c_int

        self.device.ASISetID.argtypes = [ctypes.c_int, _ASI_ID]
        self.device.ASISetID.restype = ctypes.c_int


        self.device.ASIGetGainOffset.argtypes = [ctypes.c_int,
                                            ctypes.POINTER(ctypes.c_int),
                                            ctypes.POINTER(ctypes.c_int),
                                            ctypes.POINTER(ctypes.c_int),
                                            ctypes.POINTER(ctypes.c_int)]
        self.device.ASIGetGainOffset.restype = ctypes.c_int

        self.device.ASISetCameraMode.argtypes = [ctypes.c_int, ctypes.c_int]
        self.device.ASISetCameraMode.restype = ctypes.c_int

        self.device.ASIGetCameraMode.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.device.ASIGetCameraMode.restype = ctypes.c_int

        self.device.ASIGetCameraSupportMode.argtypes = [ctypes.c_int, ctypes.POINTER(_ASI_SUPPORTED_MODE)]
        self.device.ASIGetCameraSupportMode.restype = ctypes.c_int

        self.device.ASISendSoftTrigger.argtypes = [ctypes.c_int, ctypes.c_int]
        self.device.ASISendSoftTrigger.restype = ctypes.c_int

        self.device.ASISetTriggerOutputIOConf.argtypes = [ctypes.c_int,
                                                    ctypes.c_int,
                                                    ctypes.c_int,
                                                    ctypes.c_long,
                                                    ctypes.c_long]
        self.device.ASISetTriggerOutputIOConf.restype = ctypes.c_int

        self.device.ASIGetTriggerOutputIOConf.argtypes = [ctypes.c_int,
                                                    ctypes.c_int,
                                                    ctypes.POINTER(ctypes.c_int),
                                                    ctypes.POINTER(ctypes.c_long),
                                                    ctypes.POINTER(ctypes.c_long)]
        self.device.ASIGetTriggerOutputIOConf.restype = ctypes.c_int

        self.device.ASIGetSDKVersion.restype = ctypes.c_char_p
        
    def connect(self, params: dict) -> dict:
        """
            Connect to the ASI camera | 连接ASI相机
            Args:
                params:{
                    "name" : str,
                }
            Returns:{
                "status" : int,
                "message" : str,
                "params" : {
                    "info" : BasicCameraInfo object
                }
            }
            NOTE : Name which is given should be formatted
        """
        if self.info._is_connected:
            log.logw(_("Camera is connected , please do not execute connect command again"))
            return log.return_warning(_("Camera is connected"),{})
        if self.device is not None:
            log.logw(_("Each server can only connect to one device at a time"))
            return log.return_warning(_("Each server can only connect to one device at a time"),{})
        name = params.get("name")
        if name is None:
            log.loge(_("Camera name is required,but now get a NoneType object"))
            return log.return_error(_("Camera name is required,but now get a NoneType object"),{})
        
        count = self.zwolib.ASIGetNumOfConnectedCameras()

        if count == 0:
            log.loge(_("No camera found, please check your connection"))
            return log.return_error(_("No camera found"),{"error":_("No camera found"),"advive":_("Please check your connection")})
        
        for _id in range(count):
            prop = _ASI_CAMERA_INFO()
            # Check if the camera is we needed to connect
            res = self.zwolib.ASIGetCameraProperty(prop, _id)
            if res:
                log.loge(_("Failed to get camera property"))
            prop_dict = prop.get_dict()
            if prop_dict.get("Name") == name:
                log.log(f"Found ASI camera : {name}")
                self.info._id = prop_dict.get("CameraID")
                self.info._name = prop_dict.get("Name")
                self.info._description = "ASI camera"
                # Open the camera
                res = self.device.ASIOpenCamera(_id)
                if res:
                    log.loge(_("Failed to open camera"))
                    return log.return_error(_("Failed to open camera"),{"error":_("Failed to open camera"),"advive":_("Please check your connection")})
                # Initial the camera
                res = self.device.ASIInitCamera(_id)
                if res:
                    log.loge(_("Failed to init camera"))
                    return log.return_error(_("Failed to init camera"),{"error":_("Failed to init camera")})
                log.log(_(f"Connect to {self.info._name} successfully"))
                self.info._is_connected = True
                return log.return_success(_("Connected to {self.info._name} successfully"),{})
        log.loge(_("Failed to connect to camera"))
        return log.return_error(_("Failed to connect to camera"),{})

    def disconnect(self) -> dict:
        """
            Disconnect from the ASI camera | 与ASI相机断开连接
            Args:
                None
            Returns:{
                "status" : int,
                "message" : str,
                "params" : None
            }
        """
        if self.info._is_connected:
            log.logw(_("Camera is disconnected, please do not execute disconnect command again"))
            return log.return_warning(_("Camera is disconnected"),{})
        if self.info._is_exposure:
            self.abort_exposure()
        if self.info._is_video:
            self.abort_exposure()
        res = self.device.ASICloseCamera(self.info._id)
        if res:
            log.log(_("Failed to close camera"))
            return log.return_error(_("Failed to close camera"),{})
        self.info._is_connected = False
        self.device = None
        log.log(_("Disconnected from camera successfully"))
        return log.return_success(_("Disconnected from camera successfully"),{})
    
    def reconnect(self) -> dict:
        """
            Reconnect to the ASI camera | 重连ASI相机
            Args:
                None
            Returns:{
                "status" : int,
                "message" : str,
                "params" : None
            }
        """
        if not self.info._is_connected:
            log.logw(_("Camera is not connected, please do not execute reconnect command"))
            return log.return_warning(_("Camera is not connected"),{}) 
        res = self.device.ASICloseCamera(self.info._id)
        if res:
            log.loge(_("Failed to close camera"))
            return log.return_error(_("Failed to reconnect to camera"),{"error":_("Failed to close camera")})
        res = self.device.ASIOpenCamera(self.info._id)
        if res:
            log.loge(_("Failed to open camera"))
            return log.return_error(_("Failed to reconnect camera"),{"error":_("Failed to open camera")})
        res = self.device.ASIInitCamera(self.info._id)
        if res:
            log.loge(_("Failed to init camera"))
            return log.return_error(_("Failed to init camera"),{"error":_("Failed to init camera")})
        log.log(_("Reconnect to camera successfully"))
        return log.return_success(_("Reconnect to camera successfully"))

    def scanning(self) -> dict:
        """
            Scan the ASI camera | 扫描ASI相机
            Args:
                None
            Returns:{
                "status" : int,
                "message" : str,
                "params" : {
                    "camera" : list
                }
            }
        """
        if self.device is not None and self.info._is_connected:
            log.logw(_("Please disconnect your camera before scanning"))
            return log.return_warning(_("Please disconnect your camera before scanning"),{})
        count = self.device.ASIGetNumOfConnectedCameras()
        if count == 0:
            log.loge(_("No ASI camera found"))
            return log.return_error(_("No ASI camera found"),{})
        camera_list = []
        for _id in range(count):
            # 获取相机信息
            prop = _ASI_CAMERA_INFO()
            res = self.zwolib.ASIGetCameraProperty(prop, _id)
            if res:
                log.loge(_("Failed to get camera property"))
            camera_list.append(prop.get_dict().get("Name"))
            log.logd(_(f"Camera List : {camera_list}"))
        if len(camera_list) == 0:
            log.loge(_("No ASI camera found"))
            return log.return_error(_("No ASI camera found"),{})
        log.log(_(f"Scanning ASI camera successfully , found : {camera_list}"))
        return log.return_success(_("Scanning successfully"),{"camera":camera_list})

    def polling(self) -> dict:
        """
            Polling the ASI camera infomation | 刷新ASI相机信息
            Args: None
            Returns:{
                "status" : int,
                "message" : str,
                "params" : {
                    "info" : BasicCameraInfo object
                }
            }
        """
        if self.device is None or not self.info._is_connected:
            log.logw(_("Camera is not connected, please do not execute polling command"))
            return log.return_warning(_("Camera is not connected"),{})
        res = self.info.get_dict()
        log.logd(_(f"New camera info : {res}"))
        return log.return_success(_("Camera's information is refreshed"),{"info":res})

    def get_configration(self) -> dict:
        """
            Get the camera configurationration | 刷新ASI相机配置信息
            Args: None
            Returns:{
                "status" : int,
                "message" : str,
                "params" : {
                    "info" : BasicCameraInfo object
                }
            }
        """
        if self.device is None or not self.info._is_connected:
            log.logw(_("Camera is not connected, please do not execute configuration command"))
            return log.return_warning(_("Camera is not connected"),{})
        # Get camera properties
        prop = _ASI_CAMERA_INFO()
        res = self.zwolib.ASIGetCameraProperty(prop, self.zwoinfo._id)
        if res:
            log.loge(_("Failed to get camera property"))
            return log.return_error(_("Failed to get camera property"),{"error":_("Failed to get camera property")})
        prop_dict = prop.get_dict()
        self.info._is_color = prop_dict.get("IsColorCam")
        self.info._can_cooling = prop_dict.get("IsCoolerCam")

        self.info._max_height = prop_dict.get("MaxHeight")
        self.info._max_width = prop_dict.get("MaxWidth")
        self.info._min_height = 2
        self.info._min_width = 2
        self.info._max_binning = prop_dict.get("SupportedBins")

        self.info._bayer_pattern = prop_dict.get("BayerPattern")

        self.info._pixel_height = prop_dict.get("PixelSize")
        self.info._pixel_width = prop_dict.get("PixelSize")

        self.info._depth = prop_dict.get("BitDepth")

        # Get camera frame properties
        start_x = ctypes.c_int()
        start_y = ctypes.c_int()
        res = self.zwolib.ASIGetStartPos(self.zwoinfo._id, start_x, start_y)
        if res:
            log.loge(_("Failed to get start position"))
            return log.return_error(_("Failed to get start position"),{"error":_("Failed to get start position")})
        self.info._start_x = start_x.value
        self.info._start_y = start_y.value

        number = ctypes.c_int()
        res = self.device.ASIGetNumOfControls(self.info._id,number)
        if res:
            log.loge(_("Failed to get number of controls"))
            return log.return_error(_("Failed to get number of controls"),{"error":_("Failed to get number of controls")})
        caps = _ASI_CONTROL_CAPS()
        for _caps in range(number.value):
            res = self.zwolib.ASIGetControlCaps(self.info._id, _caps, caps)
            if res:
                log.loge(_("Failed to get control capabilities"))
                return log.return_error(_("Failed to get control capabilities"),{})
            cap = caps.get_dict()
            for case in switch(cap.get("ControlType")):
                if case(ASI_CONTROL_TYPE.ASI_GAIN):
                    self.info._max_gain = cap.get("MaxValue")
                    log.logd(_(f"Max Gain : {self.info._max_gain}"))
                    self.info._min_gain = cap.get("MinValue")
                    log.logd(_(f"Min Gain : {self.info._min_gain}"))
                    self.info._gain = cap.get("DefaultValue")
                    log.logd(_(f"Current Gain : {self.info._gain}"))
                    self.info._can_gain = True
                    log.logd(_("Can Camera Gain : {self.info._can_gain}"))
                    break
                if case(ASI_CONTROL_TYPE.ASI_OFFSET):
                    self.info._max_offset = cap.get("MaxValue")
                    log.logd(_(f"Max Offset : {self.info._max_offset}"))
                    self.info._min_offset = cap.get("MinValue")
                    log.logd(_(f"Min Offset : {self.info._min_offset}"))
                    self.info._offset = cap.get("DefaultValue")
                    log.logd(_(f"Current Offset : {self.info._offset}"))
                    self.info._can_offset = True
                    log.logd(_("Can Camera Offset : {self.info._can_offset}"))
                    break
                if case(ASI_CONTROL_TYPE.ASI_TEMPERATURE):
                    self.info._temperature = cap.get("DefaultValue")
                    log.logd(_(f"Current Temperature : {self.info._temperature}"))
                    break
                if  case(ASI_CONTROL_TYPE.ASI_COOLER_ON):
                    self.info._is_cooling = cap.get("DefaultValue")
                    log.logd(_(f"Current Cooling Status : {self.info._is_cooling}"))
                    break
                if case(ASI_CONTROL_TYPE.ASI_COOLER_POWER_PERC):
                    self.info._cool_power = cap.get("DefaultValue")
                    log.logd(_(f"Current Cooling Power : {self.info._cool_power}"))
                    break
                if case(ASI_CONTROL_TYPE.ASI_EXPOSURE):
                    self.info._exposure = cap.get("DefaultValue")
                    log.logd(_(f"Current Exposure : {self.info._exposure}"))
                    self.info._max_exposure = cap.get("MaxValue")
                    log.logd(_(f"Max Exposure : {self.info._max_exposure}"))
                    break
                break
        
    def set_configration(self, params: dict) -> dict:
        return super().set_configration(params)

    def load_configration(self) -> dict:
        return super().load_configration()

    def save_configration(self) -> dict:
        """
            Save configration of camera
            Args : None
            Return : {
                "status" : int,
                "message" : str,
                "params" : None
            }
        """
        _p = path.join
        _path = _p("config",_p("camera",self.info._name+".json"))
        if not path.exists("config"):
            mkdir("config")
        if not path.exists(_p("config","camera")):
            mkdir(_p("config","camera"))
        self.info._configration = _path
        with open(_path,mode="w+",encoding="utf-8") as file:
            file.write(dumps(self.info.get_dict(),indent=4,ensure_ascii=False))
        log.log(_("Save camera information successfully"))
        return log.return_success(_("Save camera information successfully"),{})

    def start_exposure(self, params : dict) -> dict:
        """
            Start exposure function | 开始曝光
            Args : {
                "params" : {
                    "exposure" : float # exposure time
                    "gain" : int # gain
                    "offset" : int # offset
                    "binning" : int # binning
                    "image" : {
                        "is_save" : bool
                        "is_dark" : bool
                        "name" : str
                        "type" : str # fits or tiff of jpg
                    }
                    "filterwheel" : {
                        "enable" : boolean # enable or disable
                        "filter" : int # id of filter
                    }
                }
            }
            Returns : {
                "status" : int ,
                "message" : str,
                "params" : None
            }
            NOTE : This function is a blocking function
        """
        if self.device is None or not self.info._is_connected:
            log.logw(_("Camera is not connected, please do not execute polling command"))
            return log.return_warning(_("Camera is not connected"),{})
        exposure = params.get("exposure")
        gain = params.get("gain")
        offset = params.get("offset")
        binning = params.get("binning")

        is_save = params.get("image").get("is_save")
        is_dark = params.get("image").get("is_dark")
        name = params.get("image").get("name")
        _type = params.get("image").get("type")
        if params.get("filterwheel") is not None:
            filterwheel = params.get("filterwheel").get("enable")
            filter = params.get("filterwheel").get("filter")

        if exposure is None or not self.info._min_exposure < exposure < self.info._max_exposure:
            log.loge(_("Please provide a reasonable exposure value"))
            return log.return_error(_("Exposure must be reasonable"),{"error":exposure})
        log.logd(_(f"Exposure time : {exposure}"))
        
        # Set camera gain value
        res = self.zwolib.ASISetControlValue(self.info._id, ASI_CONTROL_TYPE.ASI_GAIN, gain, False)
        if res:
            log.loge(_("Failed to set camera gain value"))
            return log.return_error(f"Failed to set gain : {res}")
        self.info._gain = gain

        # Set camera offset value
        res = self.zwolib.ASISetControlValue(self.info._id, ASI_CONTROL_TYPE.ASI_OFFSET, offset, False)
        if res:
            log.loge(_("Failed to set camera offset value"))
            return log.return_error(f"Failed to set offset : {res}")
        self.info._offset = offset

        # Set camera binning value
        if binning is None or not 0 < binning < self.info._max_binning:
            log.loge(_("Please provide a valid binning value , use the default value 1"))
        if self.info._depth == 8:
            res = self.zwolib.ASISetROIFormat(self.info._id, self.info._width, self.info._height, binning, ASI_IMGTYPE.ASI_IMG_RAW8)
        elif self.info._depth == 16:
            res = self.zwolib.ASISetROIFormat(self.info._id, self.info._width, self.info._height, binning, ASI_IMGTYPE.ASI_IMG_RAW16)

        status = ctypes.c_int()
        res = self.zwolib.ASIGetExpStatus(self.info._id, status)
        if res:
            log.loge(_("Failed to get camera exposure status"))
            return log.return_error(_("Failed to get camera exposure status"),{"error":res})
        for case in switch(status.value):
            if case(ASI_EXPOSURE_STATUS.ASI_EXP_IDLE):
                break
            if case(ASI_EXPOSURE_STATUS.ASI_EXP_FAILED):
                break
            if case(ASI_EXPOSURE_STATUS.ASI_EXP_SUCCESS):
                break
            if case(ASI_EXPOSURE_STATUS.ASI_EXP_WORKING):
                log.loge(_("Camera is busy , please wait for a moment before continuing start_exposure()"))
                return log.return_error(_("Camera is busy"),{})
        try:
            res = self.device.ASIStartExposure(self.info._id,is_dark)
            if res:
                log.loge(_("Failed to start exposure"))
                return log.return_error(_("Failed to start exposure"),{"error":res})
            self.info._is_exposure = True
            sleep(0.1)
            res = self.zwolib.ASIGetExpStatus(self.zwoinfo._id, status)
            used_time = 0.0
            while status == ASI_EXPOSURE_STATUS.ASI_EXP_WORKING:
                res = self.zwolib.ASIGetExpStatus(self.zwoinfo._id, status)
                if res:
                    log.loge(_("Failed to get camera exposure status"))
                    return log.return_error(_("Failed to get camera exposure status"),{"error":res})
                if status == ASI_EXPOSURE_STATUS.ASI_EXP_FAILED:
                    log.loge(_("Some error occurred while camera exposuring"))
                    return log.return_error(_("Some error occurred while camera exposuring"),{"error":res})
                log.logd(_(f"Had already used time : {used_time}"))
                used_time += 0.1
                sleep(0.1)
                if used_time + self.info._timeout > exposure:
                    log.loge(_("Exposure timeout"))
                    return log.return_error(_("Exposure timeout"),{"error":exposure})
        finally:
            self.info._is_exposure = False
        
        res = self.zwolib.ASIGetExpStatus(self.zwoinfo._id, status)
        if status != ASI_EXPOSURE_STATUS.ASI_EXP_SUCCESS:
            log.loge(_("Camera exposure failed"))
            return log.return_error(_("Camera exposure failed"),{"error":status})
        log.log(_("Camera exposure succeeded"))
        return log.return_success(_("Camera exposure succeeded"))

    def abort_exposure(self) -> dict:
        """
        Abort exposure operation | 停止曝光
            Args: None
            Returns:{
                "status" : int,
                "message" : str
                "params" : None
            }
            NOTE : This function must be called if exposure is still in progress when shutdown server
        """
        if self.device is None and not self.info._is_connected:
            log.logw(_(f"Cannot abort exposure, device is not connected"))
            return log.return_error(_("Device is not connected"),{"error": "Device is not connected"})
        if not self.info._is_exposure:
            log.logw(_("Exposure not started , please do not execute abort_exposure() command"))
            return log.return_warning(_("Exposure not started"),{})
        res = self.device.ASIStopExposure(self.zwoinfo._id)
        if res:
            log.loge(_("Failed to stop exposure"))
            return log.return_error(_("Failed to stop exposure"),{"error":res})
        self.info._is_exposure = False
        log.log(_("Abort camera exposure successfully"))
        return log.return_success(_("Aborted camera exposure successfully"),{})

    def get_exposure_status(self) -> dict:
        """
            Get exposure status | 获取曝光状态
            Args: None
            Returns:{
                "status" : int,
                "message" : str
                "params" : {
                    "status" : int
                }
            }
        """
        if not self.info._is_connected:
            log.logw(_(f"Cannot get exposure status, device is not connected"))
            return log.return_error(_("Device is not connected"),{"error": "Device is not connected"})
        if not self.info._is_exposure:
            log.logw(_(f"Exposure not started, please do not execute get_exposure_status() command"))
            return log.return_warning(_("Exposure not started"),{})
        status = ctypes.c_int()
        res = self.zwolib.ASIGetExpStatus(self.info._id, status)
        if res:
            log.loge(_("Failed to get camera exposure status"))
            return log.return_error(_("Failed to get camera exposure status"),{"error":res})
        for case in switch(status.value):
            if case(ASI_EXPOSURE_STATUS.ASI_EXP_IDLE):
                self.info._is_exposure = False
                log.logd(_("Camera is idle and can start exposure"))
                return log.return_success(_("Camera is idle"),{"status":0})
            if case(ASI_EXPOSURE_STATUS.ASI_EXP_FAILED):
                log.logd(_("Camera exposure failed"))
                return log.return_error(_("Camera exposure failed"),{"status":1})
            if case(ASI_EXPOSURE_STATUS.ASI_EXP_SUCCESS):
                log.logd(_("Camera exposure succeeded"))
                return log.return_success(_("Camera exposure succeeded"),{"status":0})
            if case(ASI_EXPOSURE_STATUS.ASI_EXP_WORKING):
                log.loge(_("Camera is busy , please wait for a moment before continuing start_exposure()"))
                return log.return_error(_("Camera is busy"),{})

    def get_exposure_result(self) -> dict:
        """
            Get exposure result when exposure successful | 曝光成功后获取图像
            Args: None
            Returns:{
                "status" : int,
                "message" : str
                "params" : {
                    "image" : Base64 encoded image
                    "histogram" : List
                    "info" : Image Info
                }
            }
            NOTE : Format!
        """
        if not self.info._is_connected:
            log.logw(_(f"Cannot get exposure result, device is not connected"))
            return log.return_error(_("Device is not connected"),{"error": "Device is not connected"})
        if self.info._is_exposure:
            log.loge(_("Exposure is still in progress, could not get exposure result"))
            return log.return_error(_("Exposure is still in progress"),{"error": "Exposure is still in progress"})

        image_buffer = None

        # Will we need to refresh the roi information when preparing to save a image?

        image_size = self.info._height * self.info._width
        if self.info._depth == 24:
            image_size *= 3
        elif self.info._depth == 16:
            image_size *= 2
        
        image_buffer = bytearray(image_size)

        cbuffer = (ctypes.c_char * len(image_buffer)).from_buffer(image_buffer)
        res = self.zwolib.ASIGetDataAfterExp(self.info._id, cbuffer, image_size)
        if res:
            log.loge(_("Failed to get exposure result"))
            return log.return_error(_("Failed to get exposure result"),{"error": res})
        
        image = None
        image_shape = [self.info._height, self.info._width]
        if self.info._depth == 24:
            image = np.frombuffer(buffer=image_buffer, dtype=np.uint8)
            image_shape.append(3)
        elif self.info._depth == 16:
            image = np.frombuffer(buffer=image_buffer, dtype=np.uint16)
        elif self.info._depth == 8:
            image = np.frombuffer(buffer=image_buffer, dtype=np.uint8)
        else:
            image = np.frombuffer(buffer=image_buffer, dtype=np.uint8)
        
        image = image.reshape(image_shape)
        if len(image.shape) == 3:
            img = img[:,:,::-1] # convert BGR to RGB
        
        # calculate histogram of the image
        hist = None
        if self.info._depth == 8:
            hist , bins = np.histogram(image,bins=[i for i in range(1,256)])
        elif self.info._depth == 16:
            hist , bins = np.histogram(image,bins=[i for i in range(1,65536)])
        # convert image into base64 format
        # Create a base64 encoded image
        bytesio = BytesIO()
        np.savetxt(bytesio, image)
        base64_encode_img = b64encode(bytesio.getvalue())
        # Create a image information dict
        info = {
            "exposure" : self.info._last_exposure
        }
        
        if self.info._can_save:
            log.logd(_("Start saving image data in fits"))
            hdr = fits.Header()
            hdr['COMMENT'] = 'FITS (Flexible Image Transport System) format defined in Astronomy and'
            hdr['COMMENT'] = 'Astrophysics Supplement Series v44/p363, v44/p371, v73/p359, v73/p365.'
            hdr['COMMENT'] = 'Contact the NASA Science Office of Standards and Technology for the'
            hdr['COMMENT'] = 'FITS Definition document #100 and other FITS information.'
            if self.info._depth == 16:
                hdr['BZERO'] = 32768.0
                hdr['BSCALE'] = 1.0
            hdr['EXPOSURE'] = self.info._last_exposure
            hdr['TIME'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            hdr['BINX'] = self.info._binning[0]
            hdr['BINY'] = self.info._binning[1]
            hdr['INSTRUME'] = self.info._sensor_type
            
            if self.info._can_gain:
                hdr['GAIN'] = self.info._gain
            if self.info._can_offset:
                hdr['OFFSET'] = self.info._offset
            if self.info._can_iso:
                hdr['ISO'] = self.info._iso

            hdr["SOFTWARE"] = "LightAPT ASCOM Client"
            hdu = fits.PrimaryHDU(image, header=hdr)

            _path = "Image_" + "001" + ".fits"
            try:
                hdu.writeto(_path, overwrite=True)
            except OSError as e:
                log.loge(_(f"Error writing image , error : {e}"))
            log.logd(_("Save image successfully"))
        r = {
            "histogram" : hist,
            "image" : base64_encode_img,
            "info" : info,
        }
        return log.return_success(_("Image saved successfully"),r)
