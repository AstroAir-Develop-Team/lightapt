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

from .device import BasicDeviceAPI

class BasicCameraInfo(object):
    """
        Basic camera information container
    """

    _type = "" # type of the camera , must be given
    _name : str # name of the camera
    _id : int # id of the camera
    _description : str
    _timeout = 5
    _configration = "" # path to the configuration file

    _exposure = 0
    _gain = 0
    _offset = 0
    _iso = 0
    _binning = []
    _temperature = -256
    _cool_power = 0
    _last_exposure = 0
    _percent_complete = 0

    _image_id = 0
    _image_path = ""
    _image_type = ""
    _image_name_format = ""

    _ipaddress : str # IP address only ASCOM and INDI
    _api_version : str # API version only ASCOM and INDI

    _can_binning = False
    _can_cooling = False
    _can_gain = False
    _can_get_coolpower = False
    _can_guiding = False
    _can_has_shutter = False
    _can_iso = False
    _can_offset = False
    _can_save = True

    _is_color = False
    _is_connected = False
    _is_cooling = False
    _is_exposure = False
    _is_guiding = False
    _is_imageready = False
    _is_video = False

    _max_gain : int
    _min_gain : int
    _max_offset : int
    _min_offset : int
    _max_exposure : float
    _min_exposure : float
    _min_exposure_increment : float
    _max_binning : list

    _height : int
    _width : int
    _max_height : int
    _min_height : int
    _max_width : int
    _min_width : int
    _depth : int
    _max_adu : int
    _imgarray = False    # Now is just for ASCOM
    _bayer_pattern : int
    _bayer_offset_x : int
    _bayer_offset_y : int
    _pixel_height : float
    _pixel_width : float
    _start_x : int
    _start_y : int
    _subframe_x : int
    _subframe_y : int
    _sensor_type : str
    _sensor_name : str

    def get_dict(self) -> dict:
        """
            Returns a dictionary containing camera information
            Args : None
            Returns : dict
        """
        return {
            "type": self._type,
            "name": self._name,
            "id": self._id,
            "description": self._description,
            "timeout": self._timeout,
            "configration": self._configration,
            "current" : {
                "exposure": self._exposure,
                "gain": self._gain,
                "offset": self._offset,
                "iso": self._iso,
                "binning": self._binning,
                "temperature": self._temperature,
                "cool_power": self._cool_power,
                "percent_complete": self._percent_complete,
            },
            "ability": {
                "can_binning" : self._can_binning,
                "can_cooling" : self._can_cooling,
                "can_gain" : self._can_gain,
                "can_get_coolpower" : self._can_get_coolpower,
                "can_guiding" : self._can_guiding,
                "can_has_shutter" : self._can_has_shutter,
                "can_iso" : self._can_iso,
                "can_offset" : self._can_offset,
            },
            "status" : {
                "is_connected" : self._is_connected,
                "is_cooling" : self._is_cooling,
                "is_exposure" : self._is_exposure,
                "is_guiding" : self._is_guiding,
                "is_imageready" : self._is_imageready,
                "is_video" : self._is_video,
            },
            "properties" : {
                "max_gain" : self._max_gain,
                "min_gain" : self._min_gain,
                "max_offset" : self._max_offset,
                "min_offset" : self._min_offset,
                "max_exposure" : self._max_exposure,
                "min_exposure" : self._min_exposure,
                "max_binning" : self._max_binning,
            },
            "frame" : {
                "height" : self._height,
                "width" : self._width,
                "max_height" : self._max_height,
                "min_height" : self._min_height,
                "max_width" : self._max_width,
                "min_width" : self._min_width,
                "depth" : self._depth if self._depth is not None else 0,
                "max_adu" : self._max_adu,
                "imgarray" : self._imgarray,
                "bayer_pattern" : self._bayer_pattern,
                "bayer_offset_x" : self._bayer_offset_x,
                "bayer_offset_y" : self._bayer_offset_y,
                "pixel_height" : self._pixel_height,
                "pixel_width" : self._pixel_width,
                "start_x" : self._start_x,
                "start_y" : self._start_y,
                "subframe_x" : self._subframe_x,
                "subframe_y" : self._subframe_y,
                "sensor_type" : self._sensor_type,
                "sensor_name" : self._sensor_name,
            },
            "network" : {
                "ipaddress" : self._ipaddress,
                "api_version" : self._api_version,
            }
        }

class BasicSequenceInfo(object):
    """
        Basic sequence information container
    """

    sequence_count = 0
    sequence = []

    def get_dict(self) -> dict:
        """
            Returns a dictionary containing basic sequence information
            Args : None
            Returns : dict
        """
        return {
            "sequence_count" : self.sequence_count,
            "sequence" : self.sequence,
        }

class BasicCameraAPI(BasicDeviceAPI):
    """
        Basic Camera API
    """

    def __init__(self) -> None:
        super().__init__()

    def __del__(self) -> None:
        return super().__del__()

    # #################################################################
    #
    # Camera Basic API
    #
    # #################################################################

    def start_exposure(self, params : dict) -> dict:
        """
            Start exposure function | ????????????
            Args : {
                "params" : {
                    "exposure" : float # exposure time
                    "gain" : int # gain
                    "offset" : int # offset
                    "binning" : int # binning
                    "image" : {
                        "is_save" : bool
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
        """

    def abort_exposure(self) -> dict:
        """
            Abort exposure function | ????????????
            Args:
                None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : None
            }
        """

    def get_exposure_status(self) -> dict:
        """
            Get exposure status function | ??????????????????
            Args:
                None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : Exposure Status Object
                }
            }
            NOTE : This function should not be called if the camera is not in exposure
        """

    def get_exposure_result(self) -> dict:
        """
            Get exposure result function | ??????????????????
            Args:
                None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "image" : Base64 Encode Image Data,
                    "histogram" : List,
                    "info" : dict
                }
            }
        """

    def start_sequence_exposure(self , params : dict) -> dict:
        """
            Start exposure function | ??????????????????
            Args : {
                "params" : {
                    "exposure" : float # exposure time
                    "gain" : int # gain
                    "offset" : int # offset
                }
            }
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "results" : SeqExposureResults
                }
            }
            TODO : Args and Returns should be thinked more carefully
        """

    def abort_sequence_exposure(self) -> dict:
        """
            Abort sequence exposure | ??????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : None
            }
            NOTE : This function should not be called if the camera is not in exposure
        """

    def pause_sequence_exposure(self) -> dict:
        """
            Pause sequence exposure | ?????????????????? (Can continue)
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : None
            }
        """
    
    def continue_sequence_exposure(self) -> dict:
        """
            Continue sequence exposure | ??????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : None
            }
        """

    def get_sequence_exposure_status(self) -> dict:
        """
            Get exposure status function | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : Exposure Status Object
                }
            }
        """

    def get_sequence_exposure_result(self) -> dict:
        """
            Get the sequence exposure result | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "image" : Base64 Encode Image Data List
                    "histogram" : List,
                    "info" : dict
                }
            }
            NOTE : This function should be thinked carefully
        """

    def cooling(self, params : dict) -> dict:
        """
            Cooling function | ??????
            Args : {
                "params" : {
                    "enable" : boolean
                }
            }
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : Cooling Status Object
                }
            }
            NOTE : This function needs camera support
        """

    def cooling_to(self, params : dict) -> dict:
        """
            Cooling to temperature function | ?????????????????????
            Args : {
                "params" : {
                    "temperature" : float
                }
            }
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : Cooling Status Object
                }
            }
            NOTE : This function needs camera support
        """

    def get_cooling_status(self) -> dict:
        """
            Get cooling status function | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : Cooling Status Object
                }
            }
            NOTE : This function needs camera support
        """

    def start_video_capture(self, params : dict) -> dict:
        """
            Start video capture function | ??????????????????
            Args : {
                "params" : {
                    "path" : str
                }
            }
            Returns : {
                "status" : int,
                "message" : str,
                "params" : None
            }
        """

    def abort_video_capture(self) -> dict:
        """
            Abort video capture function | ??????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : None
            }
        """

    def get_video_capture_status(self) -> dict:
        """
            Get video capture status function | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : Video Capture Status Object
                }
            }
        """

    def get_video_capture_result(self) -> dict:
        """
            Get video capture result | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "video" : Video 
                }
            }
        """

    # #################################################################
    #
    # Camera Current Information
    #
    # #################################################################

    @property
    def gain(self) -> dict:
        """
            Get camera current gain function | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "gain" : float
                }
            }
        """

    @property
    def offset(self) -> dict:
        """
            Get camera current offset function | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "offset" : float
                }
            }
        """

    @property
    def binning(self) -> dict:
        """
            Get camera current binning function | ??????????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "binning" : int
                }
            }
        """

    @property
    def temperature(self) -> dict:
        """
            Get camera current temperature function | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "temperature" : float
                }
            }
        """

    @property
    def cooling_power(self) -> dict:
        """
            Get camera current cooling power function | ??????????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "power" : float
                }
            }
        """

    # #################################################################
    #
    # Camera Status
    #
    # #################################################################

    @property
    def is_connected(self) -> dict:
        """
            Is camera connected | ??????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
        """

    @property
    def is_exposure(self) -> dict:
        """
            Is exposure function | ???????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : int
                }
            }
        """

    @property
    def is_video(self) -> dict:
        """
            Is video function | ?????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
        """

    @property
    def is_guiding(self) -> dict:
        """
            Is guiding | ???????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
            NOTE : This function needs camera support
        """

    @property
    def is_cooling(self) -> dict:
        """
            Is camera cooling | ?????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
        """

    @property
    def is_imageready(self) -> dict:
        """
            Is imageready function | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
        """

    # #################################################################
    #
    # Camera Properties
    #
    # #################################################################    

    @property
    def maxmin_gain(self) -> dict:
        """
            Get camera max and min gain function | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "max_gain" : float,
                    "min_gain" : float
                }
        """

    @property
    def maxmin_offset(self) -> dict:
        """
            Get the maximum and minimum offset | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "max_offset" : float,
                    "min_offset" : float
                }
            }
        """

    @property
    def maxmin_exposure(self) -> dict:
        """
            Get the maximum and minimum exposure | ?????????????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "max_exposure" : float,
                    "min_exposure" : float
                }
            }
        """

    @property
    def max_bin(self) -> dict:
        """
            Get the maximum bin | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "max_bin" : int
                }
            }            
        """

    @property
    def frame(self) -> dict:
        """
            Get the current frame infomation | ??????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "height" : int, # current height of the image
                    "width" : int, # current width of the image
                    "bayer_offset_x" : int,
                    "bayer_offset_y" : int,
                    "subframe_x" : int,
                    "subframe_y" : int,
                    "start_x" : int # current start position
                    "start_y" : int # current start position
                    "pixel_height" : float,
                    "pixel_width" : float
                }
            }
        """

    @property
    def readout(self) -> dict:
        """
            Get the readout mode and info about sensor | ????????????????????????????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "readout_mode" : int,
                    "sensor_type" : str,
                    "sensor_name" : str,
                }
            }
            NOTE : This function needs camera and software support
        """

    # #################################################################
    #
    # Camera Ability
    #
    # #################################################################

    @property
    def can_binning(self) -> dict:
        """
            Check if camera can binning | ??????????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
        """

    @property
    def can_cooling(self) -> dict:
        """
            Check if camera can cooling | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
            NOTE : This function needs camera support
        """

    @property
    def can_gain(self) -> dict:
        """
            Check if camera can gain | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
            NOTE : I'm not sure whether DSLR is supported
        """

    @property
    def can_get_coolpower(self) -> dict:
        """
            Check if camera can get coolpower | ????????????????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
            NOTE : This function needs camera support
        """

    @property
    def can_guiding(self) -> dict:
        """
            Check if camera can guiding | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
        """

    @property
    def can_has_shutter(self) -> dict:
        """
            Check if camera can has shutter | ???????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
        """

    @property
    def can_iso(self) -> dict:
        """
            Check if camera can iso | ???????????????????????? ISO
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
        """

    @property
    def can_offset(self) -> dict:
        """
            Check if camera can offset | ????????????????????????
            Args : None
            Returns : {
                "status" : int,
                "message" : str,
                "params" : {
                    "status" : bool
                }
            }
            NOTE : I'm not sure whether DSLR is supported
        """