# ##### BEGIN GPL LICENSE BLOCK #####
#
#  Authors:             Thomas Larsson
#  Script copyright (C) Thomas Larsson 2014
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import os

Attributes = [
    "useHelpers", "useOffset", "useOverride",
    "useRig", "rigType", "genitalia",
    "mergeBodyParts", "mergeToProxy", "mergeMaxType",
    "useFaceShapes", "useFacePanel", "useFaceDrivers",
]

class Config:

    def __init__(self):
        self.scale = 1.0
        self.deleteHelpers = False
        self.folder = ""
        self.setDefaults()

    def __repr__(self):
        string = "<Config\n"
        for attr in Attributes:
            string += "  %s: %s\n" % (attr, getattr(self, attr))
        return string + ">"

    def fromSettings(self, settings):
        for attr in Attributes:
            setattr(self, attr, getattr(settings, attr))

        if settings.useCustomShapes:
            self.useCustomShapes = 'ALL'

        if self.useOverride:
            self.deleteHelpers = not self.useHelpers
            self.useHelpers = True
            self.name = ""
            self.description = ""
            self.bones = {}
            self.merge = {}
            if settings.genitalia == 'PENIS':
                self.usePenisRig = settings.usePenisRig
                self.mergePenis = not self.usePenisRig
            else:
                self.usePenisRig = False
                self.mergePenis = False
            self.loadPreset(os.path.join("armature/data/rigs", self.rigType.lower() + ".json"))

        return self


    def setDefaults(self):
        self.useRig = False
        self.useMasterBone = False
        self.useHeadControl = False
        self.useReverseHip = False
        self.useMuscles = False
        self.useTerminators = False
        self.useFaceRig = False
        self.genitalia = 'NONE'
        self.usePenisRig = False
        self.useLocks = True
        self.useRotationLimits = False
        self.addConnectingBones = False
        self.useQuaternionsOnly = False

        self.mergeSpine = False
        self.mergeShoulders = False
        self.mergeFingers = False
        self.mergePalms = False
        self.mergeHead = False
        self.mergePenis = True
        self.merge = None
        self.properties = {}
        self.terminals = {}

        self.useMhx = False
        self.useRigify = False

        self.useSplitBones = False
        self.useSplitNames = False
        self.useDeformBones = False
        self.useDeformNames = False
        self.useSockets = False
        self.useIkArms = False
        self.useIkLegs = False
        self.useFingers = False
        self.useElbows = False
        self.useStretchyBones = False

        self.useCustomShapes = False
        self.useConstraints = True
        self.useBoneGroups = False
        self.useCorrectives = False
        self.useExpressions = False
        self.useTPose = False
        self.useIkHair = False
        self.useLeftRight = False

        return self


    def loadPreset(self, filepath):
        from .load_json import loadJsonRelative
        struct = loadJsonRelative(filepath)
        for key in ["name", "description", "bones", "merge", "properties", "terminals"]:
            if key in struct.keys():
                setattr(self, key, struct[key])
        try:
            settings = struct["settings"]
        except KeyError:
            settings = {}
        for key,value in settings.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                print("Unknown property %s defined in armature options file %s" % (key, filepath))

        try:
            bones = struct["bones"]
        except KeyError:
            bones = None
        if bones:
            self.locale = Locale(bones=bones)


class Locale:
    def __init__(self, filepath=None, bones=[]):
        self.filepath = filepath
        self.bones = bones


    def __repr__(self):
        string = "<Locale %s:" % (self.filepath)
        #for key,bone in self.bones.items():
        #    string += "\n    %s %s" % (key,bone)
        return string + ">"


    def load(self, filepath=None):
        if self.bones:
            return
        if filepath:
            self.filepath = filepath
        struct = loadJson(self.filepath)
        #self.language = struct["language"]
        self.bones = struct["bones"]


    def rename(self, bname):
        if bname[0:4] == "DEF-":
            return "DEF-" + self.rename(bname[4:])

        try:
            return self.bones[bname]
        except KeyError:
            #print("Locale: no such bone: %s" % bname)
            pass

        words = bname.split(".", 1)
        try:
            return self.bones[words[0]] + "." + words[1]
        except KeyError:
            return bname
