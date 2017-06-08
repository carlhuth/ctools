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
    "name": "Sculpt Brushes (Sculpt: D, C, S, G)",
    # "description": "",
    # "category": "User Interface"
}


import inspect

import bpy

from ..utils import addongroup

import pie_menu


ICON_SCALE = 2.0


class PieMenuSculptBrushAddonPreferences(
    pie_menu.PieMenuPreferences, addongroup.AddonGroup,
        bpy.types.PropertyGroup):
    bl_idname = __name__

    def set_default_menus(self):
        self.menus.clear()
        make_menus(bpy.context, self)
        make_submenus(bpy.context, self)

    def draw(self, context):
        pie_menu.PieMenuPreferences.draw(self, context)
        addongroup.AddonGroup.draw(self, context)


def submenu_init(self, context):
    self.menu_items.clear()
    sculpt_tool = self["sculpt_tool"]
    brushes = [b for b in bpy.data.brushes if b.use_paint_sculpt and
               b.sculpt_tool == sculpt_tool]
    brush = context.tool_settings.sculpt.brush
    if brush in brushes:
        direction = brushes.index(brush)
    else:
        direction = 0
    self.quick_direction = direction
    for brush in brushes:
        if sculpt_tool == 'DRAW':
            icon = 'BRUSH_SCULPT_DRAW'
        else:
            icon = 'BRUSH_' + sculpt_tool
        item = self.menu_items.add()
        item.label = brush.name
        item.icon = icon
        item.execute = (
            "brush = bpy.data.brushes[self.label]\n"
            "context.tool_settings.sculpt.brush = brush")


def make_submenus(context, addon_prefs):
    init_string = \
        "\n".join([t[4:] for t in
                   inspect.getsource(submenu_init).split("\n")[1:]])
    prop = bpy.types.Brush.bl_rna.properties['sculpt_tool']
    for enum_item in prop.enum_items:
        idname = "sculpt_brush_submenu_" + enum_item.identifier
        if idname in addon_prefs.menus:
            menu = addon_prefs.menus[idname]
        else:
            menu = addon_prefs.menus.add()
            menu.idname = idname
        menu.label = enum_item.name
        menu.quick_action = 'FIXED'
        menu.radius = menu.radius
        menu.icon_scale = ICON_SCALE
        menu.icon_expand = 1.0
        menu.init = init_string
        menu["sculpt_tool"] = enum_item.identifier


def menu_init(self, context):
    execute_string = (
        "if not self.menu or event.type not in {\n"
        "         'LEFTMOUSE', 'SPACE', 'RET', 'NUMPAD_ENTER'}:\n"
        "     bpy.ops.paint.brush_select(\n"
        "         True, paint_mode='SCULPT',\n"
        "         sculpt_tool=self[\"sculpt_tool\"])\n"
        "     self.menu = \"\"\n"
    )

    self.menu_items.clear()
    brush_types = self["brush_types"]
    prop = bpy.types.Brush.bl_rna.properties['sculpt_tool']
    for brush_type in brush_types:
        enum_item = prop.enum_items[brush_type]
        item = self.menu_items.add()
        item.label = enum_item.name
        item.description = "Release key: decide, Press LeftMouse: sub menu"
        item.icon = enum_item.icon
        item["sculpt_tool_name"] = enum_item.name
        item["sculpt_tool"] = enum_item.identifier
        item.execute = execute_string

        num = 0
        for brush in bpy.data.brushes:
            if (brush.use_paint_sculpt and
                    brush.sculpt_tool == enum_item.identifier):
                num += 1
        if num > 1:
            item.menu = "sculpt_brush_submenu_" + enum_item.identifier
        else:
            item.menu = ""

    while len(self.menu_items) % 4:
        item = self.menu_items.add()
        item.type = 'SPACER'


def make_menus(context, addon_prefs):
    init_string = \
        "\n".join([t[4:] for t in
                   inspect.getsource(menu_init).split("\n")[1:]])
    # Draw
    menu = addon_prefs.menus.add()
    menu.icon_scale = ICON_SCALE
    menu.icon_expand = 1.0
    menu.quick_action = 'FIXED'
    menu.idname = "sculpt_brush_draw"
    menu.label = "Brush Select"
    menu.quick_action_index = 0
    menu.init = init_string
    # menu.radius = 0
    # menu.item_order = 'OFFICIAL'
    menu["brush_types"] = ['DRAW', 'CLAY', 'CLAY_STRIPS', 'INFLATE', 'BLOB',
                           'LAYER', 'CREASE']

    # Clay
    menu = addon_prefs.menus.add()
    menu.icon_scale = ICON_SCALE
    menu.icon_expand = 1.0
    menu.quick_action = 'FIXED'
    menu.idname = "sculpt_brush_clay"
    menu.label = "Brush Select"
    menu.quick_action_index = 1
    menu.init = init_string
    menu["brush_types"] = ['DRAW', 'CLAY', 'CLAY_STRIPS', 'INFLATE', 'BLOB',
                           'LAYER', 'CREASE']

    # Smooth
    menu = addon_prefs.menus.add()
    menu.icon_scale = ICON_SCALE
    menu.icon_expand = 1.0
    menu.quick_action = 'FIXED'
    menu.idname = "sculpt_brush_smooth"
    menu.label = "Brush Select"
    menu.quick_action_index = 0
    menu.init = init_string
    menu["brush_types"] = ['SMOOTH', 'FLATTEN', 'FILL', 'SCRAPE', 'PINCH']

    # Grub
    menu = addon_prefs.menus.add()
    menu.icon_scale = ICON_SCALE
    menu.icon_expand = 1.0
    menu.quick_action = 'FIXED'
    menu.idname = "sculpt_brush_grub"
    menu.label = "Brush Select"
    menu.quick_action_index = 0
    menu.init = init_string
    menu["brush_types"] = ['GRAB', 'ROTATE', 'THUMB', 'SNAKE_HOOK', 'NUDGE',
                           'MASK']


menu_keymap_items = {
    "sculpt_brush_draw": [
        ["Sculpt", {"type": 'D', "value": 'PRESS'}],
    ],
    "sculpt_brush_clay": [
        ["Sculpt", {"type": 'C', "value": 'PRESS'}],
    ],
    "sculpt_brush_smooth": [
        ["Sculpt", {"type": 'S', "value": 'PRESS'}],
    ],
    "sculpt_brush_grub": [
        ["Sculpt", {"type": 'G', "value": 'PRESS'}],
    ],
}


classes = [
    PieMenuSculptBrushAddonPreferences
]


@PieMenuSculptBrushAddonPreferences.register_addon
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    addon_prefs = PieMenuSculptBrushAddonPreferences.get_instance()
    # if "menus" not in addon_prefs:
    addon_prefs.set_default_menus()

    pie_menu.register_addon(addon_prefs)

    for idname, km_items in menu_keymap_items.items():
        for km_name, kwargs in km_items:
            km = pie_menu.get_keymap(km_name)
            if km:
                kmi = km.keymap_items.new("wm.pie_menu", **kwargs)
                kmi.properties.menu = idname


@PieMenuSculptBrushAddonPreferences.unregister_addon
def unregister():
    addon_prefs = PieMenuSculptBrushAddonPreferences.get_instance()
    pie_menu.unregister_addon(addon_prefs)
    for cls in classes[::-1]:
        bpy.utils.unregister_class(cls)
