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
    "name": "Snap Menu (3D View: Shift + TAB, Shift + Ctrl + TAB)",
    # "description": "",
    # "category": "User Interface"
}


import inspect

import bpy

from ..utils import addongroup

import pie_menu


class PieMenuSnapAddonPreferences(
    pie_menu.PieMenuPreferences, addongroup.AddonGroup,
        bpy.types.PropertyGroup):
    bl_idname = __name__

    def set_default_menus(self):
        self.menus.clear()
        make_menus(bpy.context, self)

    def draw(self, context):
        pie_menu.PieMenuPreferences.draw(self, context)
        addongroup.AddonGroup.draw(self, context)


def snap_element_init(self, context):
    def get_enum_items(obj, prop_name):
        prop = obj.bl_rna.properties[prop_name]
        return list(prop.enum_items)

    self.menu_items.clear()
    ToolSettings = bpy.types.ToolSettings

    enum_items = {e.identifier: e for e in
                  get_enum_items(ToolSettings, "snap_element")}
    identifiers = ['VERTEX', 'EDGE', 'FACE', None,'VOLUME', 'INCREMENT',
                   None, None]
    for identifier in identifiers:
        item = self.menu_items.add()
        if identifier is None:
            item.type = 'SPACER'
        else:
            enum_item = enum_items[identifier]
            item.label = enum_item.name
            item.description = enum_item.description
            item.icon = enum_item.icon
            item.execute = \
                "bpy.ops.wm.context_set_enum(" \
                "data_path='tool_settings.snap_element', " \
                "value='{}')".format(identifier)
            if identifier == 'INCREMENT':
                item.execute += (
                    "\nbpy.ops.wm.context_set_boolean(data_path="
                    "'tool_settings.use_snap_grid_absolute', value=False)")

    prop = ToolSettings.bl_rna.properties["use_snap_grid_absolute"]
    item = self.menu_items[6]
    item.type = 'ADVANCED'
    item.label = prop.name
    item.description = prop.description
    item.icon = prop.icon
    item.execute = (
        "bpy.ops.wm.context_set_enum("
        "data_path='tool_settings.snap_element', "
        "value='INCREMENT')\n"
        "bpy.ops.wm.context_set_boolean(data_path="
        "'tool_settings.use_snap_grid_absolute', value=True)")

    item = self.menu_items[3]
    item.label = "Toggle Snap"
    item.type = 'ADVANCED'
    prop = ToolSettings.bl_rna.properties["use_snap"]
    item.description = prop.description
    item.icon = 'SNAP_ON'
    item.execute = "wm.context_toggle(" \
                          "data_path='tool_settings.use_snap')"
    item.shortcut = 'TAB'


def snap_target_init(self, context):
    def get_enum_items(obj, prop_name):
        prop = obj.bl_rna.properties[prop_name]
        return list(prop.enum_items)

    self.menu_items.clear()
    for enum_item in get_enum_items(bpy.types.ToolSettings,
                                    "snap_target"):
        item = self.menu_items.add()
        item.label = enum_item.name
        item.description = enum_item.description
        item.icon = enum_item.icon
        item.execute = "wm.context_set_enum(" \
                              "data_path='tool_settings.snap_target', " \
                              "value='{}')".format(enum_item.identifier)


def make_menus(context, addon_prefs):
    # Snap Element
    menu = addon_prefs.menus.add()
    menu.idname = "snap_element"
    menu.label = "Snap Element"
    menu.next = "snap_target"
    menu.init = \
        "\n".join([t[4:] for t in
                   inspect.getsource(snap_element_init).split("\n")[1:]])

    # Snap Target
    menu = addon_prefs.menus.add()
    menu.idname = "snap_target"
    menu.label = "Snap Target"
    menu.prev = "snap_element"
    menu.init = \
        "\n".join([t[4:] for t in
                   inspect.getsource(snap_target_init).split("\n")[1:]])

    # Snap
    menu = addon_prefs.menus.add()
    menu.idname = "snap"
    menu.label = "Snap"
    menu.item_order = 'CW6'

    item = menu.menu_items.add()
    item.label = "Selection to Grid"
    item.icon = 'VERTEXSEL'
    item.execute = "view3d.snap_selected_to_grid"

    item = menu.menu_items.add()
    item.label = "Selection to Cursor"
    item.icon = 'VERTEXSEL'
    item.execute = "view3d.snap_selected_to_cursor(use_offset=False)"

    item = menu.menu_items.add()
    item.label = "Selection to Cursor (Offset)"
    item.icon = 'VERTEXSEL'
    item.execute = "view3d.snap_selected_to_cursor(use_offset=True)"

    item = menu.menu_items.add()
    item.label = "Selection to Active"
    item.icon = 'VERTEXSEL'
    item.execute = "view3d.snap_selected_to_active"

    item = menu.menu_items.add()
    item.label = "Cursor to Selected"
    item.icon = 'CURSOR'
    item.execute = "view3d.snap_cursor_to_selected"

    item = menu.menu_items.add()
    item.label = "Cursor to Center"
    item.icon = 'CURSOR'
    item.execute = "view3d.snap_cursor_to_center"

    item = menu.menu_items.add()
    item.label = "Cursor to Grid"
    item.icon = 'CURSOR'
    item.execute = "view3d.snap_cursor_to_grid"

    item = menu.menu_items.add()
    item.label = "Cursor to Active"
    item.icon = 'CURSOR'
    item.execute = "view3d.snap_cursor_to_active"


class Snap:
    idname = "snap"
    label = "Snap"
    item_order = 'CW6'
    # draw_type = 'BOX'
    # highlight = 'LAST'
    # highlight_index = 2
    # quick_action = 'LAST'

    keymap_items = [["3D View", {"type": 'S', "value": 'PRESS',
                                 "shift": True}]]

    def __init__(self, context):
        def add(name):
            item = Empty(name)
            self.items.append(item)
            return item

        self.menus = {}

        try:
            import ctools.utils.unitsystem
            add_item = True
        except:
            add_item = False
        if add_item and context.mode == 'EDIT_MESH':
            item = Empty("Mesh Selection to View Grid")
            item.icon = 'VERTEXSEL'
            item.poll = "return context.mode == 'EDIT_MESH'"

            def execute(self, context):
                import bmesh
                import ctools.utils.unitsystem
                from mathutils import Matrix
                rv3d = context.region_data
                mat4 = rv3d.view_matrix.to_3x3().to_4x4()
                v3d = context.space_data
                if hasattr(v3d, "use_local_grid") and v3d.use_local_grid:
                    mat4 = mat4 * Matrix.Translation(
                        -v3d.local_grid_location)
                unit_system = ctools.utils.unitsystem.UnitSystem(context)
                actob = context.active_object
                mat = mat4 * actob.matrix_world
                imat = mat.inverted()
                bm = bmesh.from_edit_mesh(actob.data)
                for eve in (v for v in bm.verts if v.select and not v.hide):
                    co = mat * eve.co
                    co[0] = unit_system.snap_value(
                        co[0],unit_system.grid_view)
                    co[1] = unit_system.snap_value(
                        co[1], unit_system.grid_view)
                    eve.co = imat * co
                bm.normal_update()
                bmesh.update_edit_mesh(actob.data, True)
            item.execute = MethodType(execute, item)

            self.shift_items = self.items[:]
            self.shift_items[0] = item

        # Sub Menu
        try:
            import ctools._space_view3d_snap_cursor
            add_menu = True
        except:
            import traceback
            traceback.print_exc()
            add_menu = False
        if add_menu:
            menu = type("Menu", (EmptyMenu,), {})
            menu.idname = "snap_ex"
            menu.label = "Snap EX"
            menu.items = []
            menu.prev = self.idname
            self.next = menu.idname
            self.menus[menu.idname] = menu

            def add(name):
                item = Empty(name)
                menu.items.append(item)
                return item

            item = add("Cursor to Circle")
            item.icon = 'MESH_CIRCLE'
            item.execute = "view3d.snap_cursor(mode='circle')"

            item = add("Cursor to Sphere")
            item.icon = 'MESH_UVSPHERE'
            item.execute = "view3d.snap_cursor(mode='sphere')"

            item = add("Cursor to Median")
            item.icon = 'MESH_CIRCLE'
            item.execute = "view3d.snap_cursor(mode='median')"

            item = add("Cursor to Bounding Box")
            item.icon = 'ROTATE'
            item.execute = "view3d.snap_cursor(mode='boundbox')"


menu_keymap_items = {
    "snap_element": [
        ["3D View",  {"type": 'TAB', "value": 'PRESS', "shift": True}],
    ],
    "snap_target": [
        ["3D View",  {"type": 'TAB', "value": 'PRESS', "shift": True,
                      "ctrl": True}],
    ],
    "snap": [
        ["3D View",  {"type": 'S', "value": 'PRESS', "shift": True}],
    ],
}


classes = [
    PieMenuSnapAddonPreferences
]


@PieMenuSnapAddonPreferences.register_addon
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    addon_prefs = PieMenuSnapAddonPreferences.get_instance()
    # if "menus" not in addon_prefs:
    addon_prefs.set_default_menus()

    pie_menu.register_addon(addon_prefs)

    for idname, km_items in menu_keymap_items.items():
        for km_name, kwargs in km_items:
            km = pie_menu.get_keymap(km_name)
            if km:
                kmi = km.keymap_items.new("wm.pie_menu", **kwargs)
                kmi.properties.menu = idname



@PieMenuSnapAddonPreferences.unregister_addon
def unregister():
    addon_prefs = PieMenuSnapAddonPreferences.get_instance()
    pie_menu.unregister_addon(addon_prefs)
    for cls in classes[::-1]:
        bpy.utils.unregister_class(cls)
