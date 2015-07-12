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
import json
import bpy
import math
from collections import OrderedDict

from bpy.props import *
from mathutils import *
from .drivers import *
from .utils import *
from .error import *


#------------------------------------------------------------------------
#   Bone drivers
#------------------------------------------------------------------------
'''
def addBoneDrivers(rig, propname, prefix, act):
    # The driving property names are stored in several string properties,
    # since the size of a string property in Blender is limited.
    # Joint them into one string and split it
    nchars = len(propname)
    keys = [ key for key in rig.keys() if key[0:nchars] == propname ]
    keys.sort()
    string = ":".join([rig[key] for key in keys])
    if string == "":
        return
    props = string.split(':')

    # Create the properties that will drive the bones
    initRnaProperties(rig)
    for prop in props:
        pname = prefix+prop
        rig[pname] = 0.0
        rig["_RNA_UI"][pname] = {"min":0.0, "max":1.0}

    # Collect all nonzero keyframes belonging to one bone.
    # The poses are spread out over several f-curves.
    poseTable = {}
    times = {}
    for fcu in act.fcurves:
        channel = fcu.data_path.split(".")[-1]
        idx = fcu.array_index
        if channel == "rotation_quaternion":
            if idx == 0:
                default = 1
            else:
                default = 0
        elif channel == "rotation_euler":
            default = 0
        else:
            continue

        bname = getBoneName(fcu)
        try:
            quats = poseTable[bname]
        except KeyError:
            quats = poseTable[bname] = {}

        for kp in fcu.keyframe_points:
            val = kp.co[1] - default
            if abs(val) > 1e-3:
                t = int(round(kp.co[0]))
                times[t] = True
                try:
                    quat = quats[t]
                except KeyError:
                    quat = quats[t] = Quaternion()
                quat[idx] = kp.co[1]

    # Set up a time -> used keyframe number map
    usedTimes = list(times.keys())
    usedTimes.append(1)
    usedTimes.sort()
    timeMap = {}
    for n,t in enumerate(usedTimes):
        timeMap[t] = n

    # Create drivers for the posebones.
    zeroQuat = ("1", "0", "0", "0")
    for bname,quats in poseTable.items():
        data = [[], [], [], []]
        for t,quat in quats.items():
            n = timeMap[t]
            for idx in range(1,4):
                if abs(quat[idx]) > 1e-4:
                    data[idx].append((prefix+props[n], quat[idx]))
        try:
            pb = rig.pose.bones[bname]
        except KeyError:
            pb = None
            print("Warning: Bone %s missing" % bname)
        if pb:
            addDrivers(rig, pb, "rotation_quaternion", data, zeroQuat)


class VIEW3D_OT_AddFaceRigDriverButton(bpy.types.Operator):
    bl_idname = "mhx2.add_facerig_drivers"
    bl_label = "Add Facerig Drivers"
    bl_description = "Control face rig with rig properties."
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        rig = context.object
        return (rig and rig.MhxFaceRig)

    def execute(self, context):
        rig = context.object
        act = rig.animation_data.action
        addBoneDrivers(rig, "MhxFaceShapeNames", "Mfa", act)
        rig.animation_data.action = None
        rig.MhxFaceRigDrivers = True
        return{'FINISHED'}
'''

#------------------------------------------------------------------------
#   Bone drivers
#------------------------------------------------------------------------

def getStruct(filename, struct):
    from collections import OrderedDict
    if struct is None:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        struct = json.load(open(filepath, 'rU'), object_pairs_hook=OrderedDict)
    return struct

#------------------------------------------------------------------------
#   Face poses
#------------------------------------------------------------------------

_FacePoses = None

def getFacePoses(rig = None):
    from collections import OrderedDict
    global _FacePoses
    if _FacePoses is None:
        filepath = os.path.join(os.path.dirname(__file__), "data/hm8/faceshapes/faceposes.mxa")
        _FacePoses = json.load(open(filepath, 'rU'), object_pairs_hook=OrderedDict)
    if rig:
        checkRoll(rig)
    print(_FacePoses)
    return _FacePoses


def checkRoll(rig):
    try:
        jaw = rig.data.bones["jaw"]
    except KeyError:
        return
    if abs(getRoll(jaw)) > math.pi/2:
        raise MhxError(
            "Jaw bone has wrong roll value\n" +
            "Export from newrig repo")

#------------------------------------------------------------------------
#   Add bone drivers
#------------------------------------------------------------------------

def addBoneDrivers(rig, prefix, poses):
    initRnaProperties(rig)
    for prop in poses.keys():
        pname = prefix+prop
        rig[pname] = 0.0
        rig["_RNA_UI"][pname] = {"min":0.0, "max":1.0}

    bdrivers = {}
    for pose,bones in poses.items():
        for bname,quat in bones.items():
            try:
                bdriver = bdrivers[bname]
            except KeyError:
                bdriver = bdrivers[bname] = [[],[],[],[]]
            for n in range(4):
                bdriver[n].append((prefix+pose, quat[n]))

    zeroQuat = ("1", "0", "0", "0")
    for bname,data in bdrivers.items():
        try:
            pb = rig.pose.bones[bname]
        except KeyError:
            pb = None
        if pb is None:
            bname = bname.replace(".","_")
            try:
                pb = rig.pose.bones[bname]
            except KeyError:
                print("Warning: Bone %s missing" % bname)
        if pb:
            addDrivers(rig, pb, "rotation_quaternion", data, zeroQuat)

#------------------------------------------------------------------------
#   MHPoses
#------------------------------------------------------------------------

class MHPoses(bpy.types.PropertyGroup):
    poses = {}

#------------------------------------------------------------------------
#   Animation
#------------------------------------------------------------------------

def equal(x,y):
    return ((x[0]==y[0]) and (x[1]==y[1]) and (x[2]==y[2]) and (x[3]==y[3]))


def buildAnimation(mhSkel, rig, cfg):
    if "animation" not in mhSkel.keys():
        return
    mhAnims = mhSkel["animation"]

    corr = {}
    flipmat = Matrix.Rotation(math.pi/2, 3, 'X') * Matrix.Rotation(0, 3, 'X')
    for bone in rig.data.bones:
        loc,rot,scale = bone.matrix_local.decompose()
        rmat = rot.to_matrix()
        #corr[bone.name] = flipmat.inverted() * rmat
        corr[bone.name] = rmat

    if "face-poseunits" in mhAnims.keys():
        mhAnim = mhAnims["face-poseunits"]
        mhJson = mhAnim["json"]
        poses = OrderedDict()
        poseIndex = {}
        for n,name in enumerate(mhJson["framemapping"]):
            poseIndex[n] = poses[name] = {}

        buildBvh(mhAnim["bvh"], poseIndex, corr)
        for key,value in poses.items():
            rig.MhxFacePoses.poses[key] = value

        if cfg.useFaceRigDrivers:
            addBoneDrivers(rig, "Mfa", poses)
            rig.MhxFaceRigDrivers = True

    poses = OrderedDict()
    anims = list(mhAnims.items())
    anims.sort()
    for aname,mhAnim in anims:
        if aname != "face-poseunits":
            mhBvh = mhAnim["bvh"]
            frames = mhBvh["frames"]
            poseIndex = dict([(n,{}) for n in range(len(frames))])
            buildBvh(mhBvh, poseIndex, corr)
            poses[aname] = poseIndex[0]

    if poses == {}:
        return

    if rig.animation_data:
        rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1,0,0,0)
        pb.keyframe_insert('rotation_quaternion', frame=1, group=pb.name)
    print("Poses:")
    for frame,data in enumerate(poses.items()):
        aname,pose = data
        print("  %d: %s" % (frame+2, aname))
        for pb in rig.pose.bones:
            if pb.name in pose.keys():
                pb.rotation_quaternion = pose[pb.name]
            else:
                pb.rotation_quaternion = (1,0,0,0)
            pb.keyframe_insert('rotation_quaternion', frame=frame+2, group=pb.name)


def buildBvh(mhBvh, poseIndex, corr):
    joints = mhBvh["joints"]
    #channels = mhBvh["channels"]
    frames = mhBvh["frames"]
    nJoints = len(joints)
    nFrames = len(frames)

    d2r = math.pi/180
    for m,frame in enumerate(frames):
        pose = poseIndex[m]
        for n,vec in enumerate(frame):
            x,y,z = vec
            euler = Euler((x*d2r, y*d2r, z*d2r), 'XZY')
            quat = euler.to_quaternion()
            if abs(quat.to_axis_angle()[1]) > 1e-4:
                joint = joints[n]
                if joint in corr.keys():
                    cmat = corr[joint]
                    qmat = cmat.inverted() * euler.to_matrix() * cmat
                    pose[joint] = qmat.to_quaternion()

#------------------------------------------------------------------------
#   Buttons
#------------------------------------------------------------------------

class VIEW3D_OT_AddFaceRigDriverButton(bpy.types.Operator):
    bl_idname = "mhx2.add_facerig_drivers"
    bl_label = "Add Facerig Drivers"
    bl_description = "Control face rig with rig properties."
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        rig = context.object
        return (rig and rig.MhxFaceRig and not rig.MhxFaceRigDrivers)

    def execute(self, context):
        global _FacePoses
        rig = context.object
        poses = rig.MhxFacePoses.poses
        #poses = getFacePoses(rig)["poses"]
        addBoneDrivers(rig, "Mfa", poses)
        rig.MhxFaceRigDrivers = True
        return{'FINISHED'}


def removeBoneDrivers(rig, prefix, poses):
    bnames = {}
    for pose,bones in poses.items():
        prop = prefix+pose
        del rig[prop]
        for bname in bones.keys():
            bnames[bname] = True
    for bname in bnames:
        try:
            pb = rig.pose.bones[bname]
        except KeyError:
            continue
        pb.driver_remove("rotation_quaternion")


class VIEW3D_OT_RemoveFaceRigDriverButton(bpy.types.Operator):
    bl_idname = "mhx2.remove_facerig_drivers"
    bl_label = "Remove Facerig Drivers"
    bl_description = "Remove rig property control of face rig."
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        rig = context.object
        return (rig and rig.MhxFaceRigDrivers)

    def execute(self, context):
        global _FacePoses
        rig = context.object
        poses = rig.MhxFacePoses.poses
        #poses = getFacePoses(rig)["poses"]
        removeBoneDrivers(rig, "Mfa", poses)
        rig.MhxFaceRigDrivers = False
        return{'FINISHED'}
