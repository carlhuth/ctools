# ##### BEGIN GPL LICENSE BLOCK #####
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


bl_info = {
    'name': 'Private Add-on',
    'author': 'chromoly',
    'version': (0, 1, 0),
    'blender': (2, 78, 0),
    'location': '',
    'description': 'Collection of add-ons',
    'warning': '',
    'wiki_url': '',
    'category': 'User Interface',
}


import importlib


if 'bpy' in locals():
    importlib.reload(addongroup)
    CToolsPrivatePreferences.reload_sub_modules()
else:
    from ..utils import addongroup

import bpy


class CToolsPrivatePreferences(
        addongroup.AddonGroupPreferences,
        bpy.types.AddonPreferences if '.' not in __name__ else
        bpy.types.PropertyGroup):
    bl_idname = __name__

    sub_modules = [
        'space_view3d_colorwire',
        # 'fakeknife',
        'space_view3d_localgrid',
        # 'piemenu',
        # 'snapcursor',
        # 'utilitymenu',
        # 'vertexslide',
        # 'addkeymaps',
    ]


classes = [
    CToolsPrivatePreferences,
]


@CToolsPrivatePreferences.register_addon
def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes[::-1]:
        bpy.utils.unregister_class(cls)
