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
    'name': 'Panel Restriction',
    'author': 'chromoly',
    'version': (0, 1, 2),
    'blender': (2, 78, 0),
    'location': 'TOOLS > Panel Restriction, UI > Panel Restriction, '
                'SpaceProperties > WINDOW > Panel Restriction',
    'description': 'Hide panels',
    'wiki_url': '',
    'category': 'User Interface',
}


"""
任意のパネルを非表示にする。但しヘッダ無しのパネルは対象外。
"""


from collections import defaultdict, OrderedDict
import ctypes as ct
import sys
import traceback
from types import SimpleNamespace

import bpy

try:
    importlib.reload(addongroup)
    importlib.reload(customproperty)
    importlib.reload(registerinfo)
    importlib.reload(structures)
except NameError:
    from ..utils import addongroup
    from ..utils import customproperty
    from ..utils import registerinfo
    from ..utils import structures

iface = bpy.app.translations.pgettext_iface


PANEL_NAME = 'Panel Restriction'
# PANEL_HEADER_BASIC_STYLE: Falseだと名前部分でも有効・無効の切り替えが出来る
PANEL_HEADER_BASIC_STYLE = True
SHOW_EYE_ICON = False

translation_dict = {
    'ja_JP': {
        ('*', PANEL_NAME): 'パネルを隠す',
        ('*', 'Hide panels'):
            '任意のパネルを非表示にする。但しヘッダ無しのパネルは対象外',
        ('*', 'Show always'): '常に表示',
    }
}


###############################################################################
# Addon Preferences
###############################################################################
# その都度 AddonPreferencesPanelRestriction.get_instance() を呼び出していては遅いので
# global変数に格納しておく
addon_preferences = None


class Temp(SimpleNamespace):
    """必要に応じて addon_prefs_key と panel_header_key の引数に使用する"""


def addon_prefs_key(space, region):
    key = 'use_panel_' + space.type.lower() + '_' + region.type.lower()
    if space.type == 'PROPERTIES':
        ctx = space.context.lower()
        if ctx == 'particles':
            ctx = 'particle'
        key += '_' + ctx
    return key


def panel_header_key(space, region):
    key = 'restrict_' + region.type.lower()
    if space.type == 'PROPERTIES':
        ctx = space.context.lower()
        if ctx == 'particles':
            ctx = 'particle'
        key += '_' + ctx
    return key


def gen_addon_prefs_name_space():
    name_space = OrderedDict()

    prop = bpy.types.Space.bl_rna.properties['type']
    space_names = {e.identifier: e.name for e in prop.enum_items}
    prop = bpy.types.Region.bl_rna.properties['type']
    region_names = {e.identifier: e.name for e in prop.enum_items}
    for space_type, region_types in registerinfo.area_region_types.items():
        if space_type == 'PROPERTIES':
            for bl_context, (_, space_context_name) in \
                    registerinfo.bl_context_properties.items():
                space = Temp(type=space_type, context=bl_context)
                region = Temp(type='WINDOW')
                attr = addon_prefs_key(space, region)
                name = '{}: {}'.format(space_names[space_type],
                                       space_context_name)
                if bl_context in {'constraint', 'bone_constraint', 'modifier'}:
                    default = False
                else:
                    default = True
                name_space[attr] = bpy.props.BoolProperty(
                    name=name,
                    default=default)
        else:
            for region_type in region_types:
                if region_type in {'UI', 'TOOLS'}:
                    space = Temp(type=space_type, context='')
                    region = Temp(type=region_type)
                    attr = addon_prefs_key(space, region)
                    name = '{}: {}'.format(space_names[space_type],
                                           region_names[region_type])
                    if space_type in {'VIEW_3D'}:
                        default = True
                    else:
                        default = False
                    name_space[attr] = bpy.props.BoolProperty(
                        name=name,
                        default=default
                    )
    return name_space


_AddonPreferencesPanelRestriction = type(
    '_AddonPreferencesPanelRestriction',
    (),
    gen_addon_prefs_name_space()  # python3.6なら順番を維持してくれる
)


class AddonPreferencesResrictPanels(
        _AddonPreferencesPanelRestriction,
        addongroup.AddonGroupPreferences,
        registerinfo.AddonRegisterInfo,
        bpy.types.PropertyGroup if '.' in __name__ else
        bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout

        split = layout.split()
        column1 = split.column()
        column2 = split.column()

        props = [prop for prop in self.bl_rna.properties
                 if prop.identifier.startswith('use_panel_')]
        if sys.version_info.minor < 6:  # python-3.5
            props.sort(key=lambda p: p.identifier)

        for prop in props:
            attr = prop.identifier
            if attr.startswith('use_panel_properties_'):
                row = column2.row()
            else:
                row = column1.row()
            row.prop(self, attr)

        layout.separator()
        super().draw(context)


###############################################################################
# UILayout.label()
###############################################################################
# 未使用
def draw_pinned_icon(context_p, layout_p):
    """UILayoutのポインタアドレス(as_pointer()で得られる値)のみが
    分かっている状態でUILayout.label()を呼び出す。

    PINNEDアイコンの描画のみ行う。
    """
    func = bpy.types.UILayout.bl_rna.functions['label']
    function_rna = ct.cast(func.as_pointer(),
                           ct.POINTER(structures.FunctionRNA)).contents

    text = ct.c_char()
    text_ctxt = ct.c_char()

    ptr = structures.PointerRNA()
    ptr.data = layout_p
    params = structures.ParameterList()
    t = ct.c_char * (8 + 8 + 4 + 4 + 4)
    data = t()
    addr = ct.addressof(data)
    n = ct.sizeof(ct.c_void_p)
    # text
    p = ct.cast(addr, ct.POINTER(ct.c_void_p))
    p.contents.value = ct.addressof(text)
    addr += n
    # text_ctxt
    p = ct.cast(addr, ct.POINTER(ct.c_void_p))
    p.contents.value = ct.addressof(text_ctxt)
    addr += n
    n = ct.sizeof(ct.c_int)
    # translate
    p = ct.cast(addr, ct.POINTER(ct.c_int))
    p.contents.value = 0
    addr += n
    # icon
    p = ct.cast(addr, ct.POINTER(ct.c_int))
    p.contents.value = 43  # PINNED
    addr += n
    # icon_value
    p = ct.cast(addr, ct.POINTER(ct.c_int))
    p.contents.value = 0

    params.data = ct.addressof(data)

    function_rna.call(context_p, None, ct.byref(ptr), ct.byref(params))


###############################################################################
# get SpaceType, ARegionType
###############################################################################
try:
    _ = all_space_types
except NameError:
    all_space_types = None
    """:type: dict"""
try:
    _ = all_region_types
except NameError:
    all_region_types = None
    """:type: dict"""


def get_space_types():
    """
    :rtype: dict[str, T]
    """
    # 起動時やアドオンリロード時のregister内ではrestrict云々でエラーが出る
    # のでそれを回避するよう気をつける
    screen = bpy.context.window.screen
    area = screen.areas[0]
    sa = structures.ScrArea.cast(area)

    st_p = sa.type
    st = None
    while st_p:
        st = st_p.contents
        st_p = st.prev

    space_types = {}
    while st:
        for e in structures.RNAEnumSpaceTypeItems:
            if e.value == st.spaceid:
                if e.name != 'EMPTY':
                    space_types[e.name] = st
                break
        if st.next:
            st = st.next.contents
        else:
            st = None
    return space_types


def get_region_types():
    """
    :return: {'VIEW_3D': {'TOOLS': art, 'TOOL_PROPS': art, ...}, ...}
    :rtype: dict[str, dict[str, T]]
    """
    result = {}
    for name, st in all_space_types.items():
        d = result[name] = {}
        region_types = st.regiontypes.to_list(structures.ARegionType)
        for art in region_types:
            region_name = structures.RNAEnumRegionTypeItems(art.regionid).name
            d[region_name] = art
    return result


###############################################################################
# Overwrite poll functions
###############################################################################
poll_type = ct.CFUNCTYPE(ct.c_int, ct.c_void_p, ct.c_void_p)

original_attributes = {}
new_attributes = {}

# pt->flag & PNL_NO_HEADER
PNL_DEFAULT_CLOSED = 1
PNL_NO_HEADER = 2

# panel->flag & PNL_PIN
PNL_SELECT = 1
PNL_CLOSEX = 1 << 1
PNL_CLOSEY = 1 << 2
PNL_CLOSED = PNL_CLOSEX | PNL_CLOSEY
PNL_PIN = 1 << 5


# def UI_panel_find_by_type(ar, pt):
#     for pa in ar.panels.to_list(structures.Panel):
#         if pa.panelname == pt.idname:
#             return pa


def is_addon_panel(idname):
    """このアドオンで定義したクラスなら真を返す"""
    for cls in panel_classes:
        if idname == cls.bl_idname:
            return True
    return False


def is_visible(space, region, idname):
    test_status = False
    if region.type in {'UI', 'TOOLS'}:
        test_status = True
    else:
        if space.type == 'PROPERTIES':
            if region.type == 'WINDOW':
                test_status = True
    if test_status:
        key = addon_prefs_key(space, region)
        if not getattr(addon_preferences, key):
            return True

        try:
            wm_prop = getattr(bpy.context.window_manager,
                              SCREEN_PG_panel_restriction.WM_ATTRIBUTE)
        except:  # 無いとは思うけど
            traceback.print_exc()
            return True
        space_key = str(space.as_pointer())
        if space_key not in wm_prop.spaces:
            SCREEN_PG_panel_restriction.ensure_space(space)
        prop = wm_prop.spaces[space_key]
        attr = panel_header_key(space, region)
        if not getattr(prop, attr):
            return True

        prop = wm_prop.panels.get(idname)
        if prop:
            return prop.show_always
    return True


def get_original_attributes(panel_type=None):
    def get(pt):
        idname = pt.idname.decode('utf-8')
        if idname in original_attributes:
            return
        if is_addon_panel(idname):
            return
        poll_func = pt.poll
        if poll_func:  # 作り直し
            poll_func = poll_type(ct.cast(poll_func, ct.c_void_p).value)
        else:
            poll_func = None
        original_attributes[idname] = {
            'poll': poll_func,
        }

    if panel_type:
        get(panel_type)
    else:
        for space_type, region_types in all_region_types.items():
            for region_type, art in region_types.items():
                for pt in art.paneltypes.to_list(structures.PanelType):
                    get(pt)


def replace_attributes(panel_type=None):
    def replace(pt):
        idname = pt.idname.decode('utf-8')
        if is_addon_panel(idname):
            return
        if idname not in original_attributes:
            return

        def poll(context_p, pt_p):
            context = bpy.context
            space = context.space_data
            region = context.region

            pt = structures.PanelType.cast(pt_p)
            idname = pt.idname.decode('utf-8')

            func = original_attributes[idname]['poll']
            if func:
                if not func(context_p, pt_p):
                    return 0

            if pt.flag & PNL_NO_HEADER:
                return 1

            return is_visible(space, region, idname)

        poll_func = poll_type(poll)
        pt.poll = poll_func
        new_attributes[idname] = {
            'poll': poll_func,
        }

    if panel_type:
        replace(panel_type)
    else:
        for space_type, region_types in all_region_types.items():
            for region_type, art in region_types.items():
                for pt in art.paneltypes.to_list(structures.PanelType):
                    replace(pt)


def restore_attributes():
    for space_type, region_types in all_region_types.items():
        for region_type, art in region_types.items():
            for pt in art.paneltypes.to_list(structures.PanelType):
                idname = pt.idname.decode('utf-8')
                if is_addon_panel(idname):
                    continue
                if idname not in original_attributes:
                    continue

                attrs = original_attributes[idname]
                poll = attrs['poll']
                if poll:
                    pt.poll = poll
                else:
                    pt.poll = poll_type(0)


###############################################################################
# Panel
###############################################################################
panel_classes = []


def region_panel_categories(art, ar, all=False):
    if all:
        names = []
        for pt in art.paneltypes.to_list(structures.PanelType):
            names.append(pt.category.decode('utf-8'))
        return sorted(set(names), key=lambda x: names.index(x))

    else:
        categories = ar.panels_category.to_list(structures.PanelCategoryDyn)
        return [c.idname.decode('utf-8') for c in categories]


class _SCREEN_PT_panel_restriction:
    bl_idname = ''
    bl_space_type = ''
    bl_region_type = ''
    bl_label = PANEL_NAME if PANEL_HEADER_BASIC_STYLE else ' '
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        key = addon_prefs_key(context.space_data, context.region)
        return getattr(addon_preferences, key)

    def draw_header(self, context):
        space = context.space_data
        region = context.region
        wm_prop = getattr(context.window_manager,
                          SCREEN_PG_panel_restriction.WM_ATTRIBUTE)
        space_key = str(space.as_pointer())
        if space_key not in wm_prop.spaces:
            SCREEN_PG_panel_restriction.ensure_space(space)
        prop = wm_prop.spaces[space_key]
        attr = panel_header_key(space, region)

        row = self.layout.row(align=True)
        if PANEL_HEADER_BASIC_STYLE:
            row.prop(prop, attr, text='')
            if SHOW_EYE_ICON:
                if getattr(prop, attr):
                    icon = 'RESTRICT_VIEW_ON'
                else:
                    icon = 'RESTRICT_VIEW_OFF'
                row.prop(prop, attr, text='', icon=icon, emboss=False)
        else:
            row.prop(prop, attr, text=PANEL_NAME)

    def draw(self, context):
        space = context.space_data
        region = context.region
        wm_prop = getattr(context.window_manager,
                          SCREEN_PG_panel_restriction.WM_ATTRIBUTE)

        ar = structures.ARegion.cast(region)

        space_key = str(space.as_pointer())
        space_prop = wm_prop.spaces[space_key]

        context_p = context.as_pointer()
        art = all_region_types[space.type][region.type]

        active_panel_types = []
        for pt in art.paneltypes.to_list(structures.PanelType):
            panel_context = pt.context.decode('utf-8')
            if space.type == 'PROPERTIES' and panel_context:
                # lower()メソッドが必要な点に注意、あとparticle<>PARTICLESにも
                ctx = space.context.lower()
                if ctx == 'particles':
                    ctx = 'particle'
                if panel_context != ctx:
                    continue

            if pt.flag & PNL_NO_HEADER:
                continue

            idname = pt.idname.decode('utf-8')

            # ここでやるべきか？
            if idname not in original_attributes:
                get_original_attributes(pt)
                replace_attributes(pt)

            if idname in original_attributes:
                active_panel_types.append(pt)

        # active_panel_types.sort(key=lambda pt: pt.label.decode('utf-8'))

        enum_items = bpy.types.Context.bl_rna.properties['mode'].enum_items
        enum_items = {e.identifier: e.name for e in enum_items}

        # TOOLS, UIはカテゴリー分け、PROPERTIESはbl_context分け
        def draw_item(layout, pt):
            idname = pt.idname.decode('utf-8')

            if idname not in wm_prop.panels:
                SCREEN_PG_panel_restriction.ensure_panel(idname)

            visible = True
            is_context_fail = False
            panel_context = pt.context.decode('utf-8')
            panel_context_label = panel_context
            if space.type == 'VIEW_3D' and region.type == 'TOOLS':
                if panel_context:
                    if panel_context in registerinfo.bl_context_view3d:
                        mode = registerinfo.bl_context_view3d[
                            panel_context][0]
                        if context.mode != mode:
                            visible = False
                            is_context_fail = True
                        panel_context_label = enum_items[mode]
                    else:
                        visible = False
                        is_context_fail = True
            if visible:
                if idname in original_attributes:
                    attrs = original_attributes[idname]
                    poll = attrs['poll']
                    if poll:
                        visible = poll(context_p, ct.addressof(pt))

            if not space_prop.show_all and is_context_fail:
                return

            row = layout.row()
            sub = row.row()
            version = (bpy.app.version[0] * 1000 + bpy.app.version[1] * 10
                       + bpy.app.version[2])
            if version < 2784:
                sub.alignment = 'LEFT'
            sub.active = not is_context_fail
            sub.prop(wm_prop.panels[idname], 'show_always',
                     text=pt.label.decode('utf-8'))

            sub = row.row(align=True)
            sub.alignment = 'RIGHT'
            if space.type == 'VIEW_3D' and region.type == 'TOOLS':
                if space_prop.show_mode and panel_context_label:
                    sub.label(panel_context_label)
            icon = 'RESTRICT_VIEW_OFF' if visible else 'RESTRICT_VIEW_ON'
            sub.label(icon=icon)

        layout = self.layout.column()

        if space.type == 'VIEW_3D' and region.type == 'TOOLS':
            row = layout.row()
            row.prop(space_prop, 'show_all', text='All')
            row.prop(space_prop, 'show_mode', text='Mode')

            sub = row.row(align=True)
        else:
            sub = layout.row(align=True)
        sub.alignment = 'RIGHT'
        op = sub.operator(SCREEN_OT_panal_restriction_move.bl_idname,
                          text='', icon='TRIA_UP')
        op.region_type = region.type
        if space.type == 'PROPERTIES':
            op.space_context = space.context
        else:
            op.space_context = ''
        op.tail = False
        op = sub.operator(SCREEN_OT_panal_restriction_move.bl_idname,
                          text='', icon='TRIA_DOWN')
        op.region_type = region.type
        if space.type == 'PROPERTIES':
            op.space_context = space.context
        else:
            op.space_context = ''
        op.tail = True

        if space.type == 'PROPERTIES':
            for pt in active_panel_types:
                row = layout.row()
                draw_item(row, pt)
        else:
            categories = region_panel_categories(art, ar, all=True)
            if len(categories) > 1:
                d = defaultdict(list)
                for pt in active_panel_types:
                    d[pt.category.decode('utf-8')].append(pt)
                for category in categories:
                    if not d[category]:
                        continue
                    layout.label(iface(category) + ':')
                    for pt in d[category]:
                        draw_item(layout, pt)
            else:
                for pt in active_panel_types:
                    draw_item(layout, pt)


def generate_panel_classes():
    panel_classes.clear()

    for space_type, region_types in registerinfo.area_region_types.items():
        spacetype = space_type.replace('_', '')
        for region_type in region_types:
            if space_type == 'PROPERTIES' and region_type == 'WINDOW':
                for bl_context in registerinfo.bl_context_properties:
                    name = '{}_PT_panel_restriction_{}_{}'.format(
                        spacetype, region_type.lower(), bl_context)
                    attrs = {
                        'bl_idname': name,
                        'bl_space_type': space_type,
                        'bl_region_type': region_type,
                        'bl_context': bl_context
                    }
                    panel_class = type(
                        name, (_SCREEN_PT_panel_restriction, bpy.types.Panel),
                        attrs)
                    panel_classes.append(panel_class)

            elif region_type in {'UI', 'TOOLS'}:
                name = '{}_PT_panel_restriction_{}'.format(
                    spacetype, region_type.lower())
                attrs = {
                    'bl_idname': name,
                    'bl_space_type': space_type,
                    'bl_region_type': region_type,
                }
                if space_type == 'VIEW_3D' and region_type == 'TOOLS':
                    attrs['bl_category'] = 'Tools'  # Miscタブを作らせない為
                panel_class = type(
                    name, (_SCREEN_PT_panel_restriction, bpy.types.Panel),
                    attrs)
                panel_classes.append(panel_class)


###############################################################################
# PropertyGroup: WindowManager.panel_restriction
###############################################################################
def gen_name_space():
    """SpaceProperties用のプロパティーを作る
    """
    name_space = OrderedDict()
    bl_rna = bpy.types.SpaceProperties.bl_rna
    for enum_item in bl_rna.properties['context'].enum_items:
        space = Temp(type='PROPERTIES', context=enum_item.identifier)
        region = Temp(type='WINDOW')
        attr = panel_header_key(space, region)
        name_space[attr] = bpy.props.BoolProperty(
            name='Restrict',
            description='Hide panels'
        )
    return name_space


_SCREEN_PG_panel_restriction_space = type(
    '_SCREEN_PG_panel_restriction_space',
    (),
    gen_name_space()
)


class SCREEN_PG_panel_restriction_space(_SCREEN_PG_panel_restriction_space,
                                        bpy.types.PropertyGroup):
    restrict_tools = bpy.props.BoolProperty(
        name='Restrict',
        description='Hide panels'
    )
    restrict_ui = bpy.props.BoolProperty(
        name='Restrict',
        description='Hide panels'
    )

    # bl_contextが一致しないものも表示する。VIEW_3D-TOOLSのみ
    show_all = bpy.props.BoolProperty(
        name='Show All',
    )
    show_mode = bpy.props.BoolProperty(
        name='Show Mode',
    )


class SCREEN_PG_panel_restriction_panel(bpy.types.PropertyGroup):
    show_always = bpy.props.BoolProperty(
        name='Show Always',
        description='Show always',
        default=True)


class SCREEN_PG_panel_restriction(bpy.types.PropertyGroup):
    WM_ATTRIBUTE = 'panel_restriction'

    spaces = bpy.props.CollectionProperty(
        type=SCREEN_PG_panel_restriction_space)
    panels = bpy.props.CollectionProperty(
        type=SCREEN_PG_panel_restriction_panel)

    item_name = ''

    def _fget(self):
        return False

    def _fset_space(self, value):
        self.spaces.add().name = self.__class__.item_name

    def _fset_panel(self, value):
        self.panels.add().name = self.__class__.item_name

    add_space = bpy.props.BoolProperty(get=_fget, set=_fset_space)
    add_panel = bpy.props.BoolProperty(get=_fget, set=_fset_panel)

    @classmethod
    def ensure_space(cls, space):
        wm_prop = getattr(bpy.context.window_manager, cls.WM_ATTRIBUTE)
        item_name = str(space.as_pointer())
        if item_name not in wm_prop.spaces:
            cls.item_name = item_name
            wm_prop.add_space = True

    @classmethod
    def ensure_panel(cls, idname):
        wm_prop = getattr(bpy.context.window_manager, cls.WM_ATTRIBUTE)
        if idname not in wm_prop.panels:
            cls.item_name = idname
            wm_prop.add_panel = True

    @classmethod
    def register(cls):
        setattr(bpy.types.WindowManager, cls.WM_ATTRIBUTE,
                bpy.props.PointerProperty(type=cls))

    @classmethod
    def unregister(cls):
        delattr(bpy.types.WindowManager, cls.WM_ATTRIBUTE)


###############################################################################
# Handlers
###############################################################################
ID_PROP_SPACE_KEY = 'panel_restriction_spaces'
ID_PROP_PANEL_KEY = 'panel_restriction_panels'


@bpy.app.handlers.persistent
def save_pre(scene):
    wm = bpy.context.window_manager
    wm_prop = getattr(wm, SCREEN_PG_panel_restriction.WM_ATTRIBUTE)

    for screen in bpy.data.screens:
        screen_data = []
        for area in screen.areas:
            for space in area.spaces:
                key = str(space.as_pointer())
                if key in wm_prop.spaces:
                    prop = wm_prop.spaces[key]
                    data = dict(prop.items())
                    if 'name' in data:
                        del data['name']
                    screen_data.append(data)
                else:
                    screen_data.append({'a': 1})
        screen[ID_PROP_SPACE_KEY] = screen_data

    data = {prop.name: prop.show_always for prop in wm_prop.panels}
    bpy.data.screens[0][ID_PROP_PANEL_KEY] = data


@bpy.app.handlers.persistent
def save_post(scene):
    for screen in bpy.data.screens:
        if ID_PROP_SPACE_KEY in screen:
            del screen[ID_PROP_SPACE_KEY]
        if ID_PROP_PANEL_KEY in screen:
            del screen[ID_PROP_PANEL_KEY]


@bpy.app.handlers.persistent
def load_post(dummy):
    global addon_preferences
    addon_preferences = AddonPreferencesResrictPanels.get_instance()

    wm = bpy.context.window_manager
    wm_prop = getattr(wm, SCREEN_PG_panel_restriction.WM_ATTRIBUTE)
    wm_prop.spaces.clear()
    wm_prop.panels.clear()

    for screen in bpy.data.screens:
        if ID_PROP_SPACE_KEY in screen:
            screen_data = screen[ID_PROP_SPACE_KEY]
            i = 0
            for area in screen.areas:
                for space in area.spaces:
                    if i < len(screen_data):
                        item = wm_prop.spaces.add()
                        item.name = str(space.as_pointer())
                        for k, v in screen_data[i].items():
                            item[k] = v
                        i += 1
                    else:
                        # fullscreenでsaveすると元のscreenのspaceの数が一個多い
                        pass
            del screen[ID_PROP_SPACE_KEY]
    screen = bpy.data.screens[0]
    if ID_PROP_PANEL_KEY in screen:
        for name, show_always in screen[ID_PROP_PANEL_KEY].items():
            item = wm_prop.panels.add()
            item.name = name
            item.show_always = show_always


@bpy.app.handlers.persistent
def scene_update_pre(scene):
    global all_space_types, all_region_types
    if all_space_types is None:
        all_space_types = get_space_types()
    if all_region_types is None:
        all_region_types = get_region_types()

    get_original_attributes()
    replace_attributes()

    bpy.app.handlers.scene_update_pre.remove(scene_update_pre)


###############################################################################
# Sort Operator
###############################################################################
class SCREEN_OT_panal_restriction_move(bpy.types.Operator):
    bl_idname = 'screen.panal_restriction_move'
    bl_label = 'Move Head or Tail'
    bl_description = 'Move panel to tom or bottom'
                     # 'If any modifier key is hold, close panel'

    region_type = bpy.props.StringProperty()
    space_context = bpy.props.StringProperty()  # SpaceProperties.context
    tail = bpy.props.BoolProperty()
    close = bpy.props.BoolProperty()

    def move_head(self, area, region, space_context='', close=False):
        if space_context:
            d = {v[0]: k for k, v in
                 registerinfo.bl_context_properties.items()}
            space_context = d[space_context]

        region_types = get_region_types()

        ar = structures.ARegion.cast(region)

        # sort PanelType
        art = region_types[area.type][region.type]
        panel_types = art.paneltypes.to_list(structures.PanelType)
        pt_list = []
        for pt in panel_types:
            if is_addon_panel(pt.idname.decode('utf-8')):
                if not space_context or \
                        pt.context.decode('utf-8') == space_context:
                    pt_list.append(pt)
        if not pt_list:
            return
        if self.tail:
            for pt in pt_list:
                art.paneltypes.remove(pt)
                art.paneltypes.append(pt)
        else:
            insert_index = 0
            for i, pt in enumerate(panel_types):
                if pt.flag & PNL_NO_HEADER:
                    insert_index = i + 1
            for pt in pt_list[::-1]:
                art.paneltypes.remove(pt)
                art.paneltypes.insert(insert_index, pt)

        # sort Panel
        blocks = ar.uiblocks.to_list(structures.uiBlock)
        panels = [bl.panel.contents for bl in blocks if bl.panel]
        panels.sort(key=lambda pa: pa.sortorder)
        panels = [[pa, 0, 0] for pa in panels]
        last_offset = 0
        panel_index = 0
        insert_index = 0
        prev_panel = None

        for i, elem in enumerate(panels):
            pa = elem[0]
            pt = pa.type.contents

            if is_addon_panel(pt.idname.decode('utf-8')):
                panel_index = i
                panel = pa
            if pt.flag & PNL_NO_HEADER:
                insert_index = i + 1
                prev_panel = pa

            elem[1] = last_offset
            if pt.flag & PNL_NO_HEADER or not pa.flag & PNL_CLOSEY:
                last_offset = pa.ofsy
            else:  # close
                last_offset = pa.ofsy + pa.sizey
            elem[2] = last_offset

        if not panel:
            return
        if insert_index == len(panels):  # 並び替えの必要なし
            return

        # panel remove and insert
        if self.tail:
            panels.append(panels.pop(panel_index))
        else:
            elem = panels.pop(panel_index)
            panels.insert(panel_index, None)
            panels.insert(insert_index, elem)
            panels.remove(None)

        # calc offset
        offset = 0
        for i, elem in enumerate(panels):
            pa, top, bottom = elem
            draw_size = top - bottom
            pt = pa.type.contents

            if pt.flag & PNL_NO_HEADER or not pa.flag & PNL_CLOSEY:
                pa.ofsy = offset - draw_size
            else:  # close
                pa.ofsy = offset - (top - pa.ofsy)
            offset -= draw_size

        # update sortorder (all panels)
        if self.tail:
            for pa in ar.panels.to_list(structures.Panel):
                if pa.sortorder < panel.sortorder:
                    continue
                if pa == panel:
                    continue
                if pa.sortorder >= panel.sortorder:
                    pa.sortorder -= 1
            panel.sortorder = len(ar.panels) - 1
        else:
            for pa in ar.panels.to_list(structures.Panel):
                if prev_panel:
                    if pa.sortorder <= prev_panel.sortorder:
                        continue
                if pa == panel:
                    continue
                if not prev_panel or pa.sortorder >= prev_panel.sortorder:
                    if pa.sortorder < panel.sortorder:
                        pa.sortorder += 1
            if prev_panel:
                panel.sortorder = prev_panel.sortorder + 1
            else:
                panel.sortorder = 0

    def execute(self, context):
        if 0:
            for area in context.screen.areas:
                for region in area.regions:
                    self.move_head(area, region, '')
                area.tag_redraw()

        area = context.area
        for region in area.regions:
            if region.type == self.region_type:
                self.move_head(area, region, self.space_context, self.close)
        context.area.tag_redraw()

        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.properties.is_property_set('close'):
            close = event.shift or event.ctrl or event.alt or event.oskey
            self.close = close
        return self.execute(context)


###############################################################################
# Register, Unregister
###############################################################################
classes = [
    AddonPreferencesResrictPanels,

    SCREEN_OT_panal_restriction_move,

    SCREEN_PG_panel_restriction_space,
    SCREEN_PG_panel_restriction_panel,
    SCREEN_PG_panel_restriction,
]


@AddonPreferencesResrictPanels.register_addon
def register():
    global addon_preferences

    generate_panel_classes()

    for cls in classes:
        bpy.utils.register_class(cls)
    for cls in panel_classes:
        bpy.utils.register_class(cls)

    addon_preferences = AddonPreferencesResrictPanels.get_instance()

    bpy.app.handlers.scene_update_pre.append(scene_update_pre)
    bpy.app.handlers.save_pre.append(save_pre)
    bpy.app.handlers.save_post.append(save_post)
    bpy.app.handlers.load_post.append(load_post)

    bpy.app.translations.register(__name__, translation_dict)

    # wm = bpy.context.window_manager
    # kc = wm.keyconfigs.addon
    # if kc:
    #     km = Preferences.get_keymap('Mesh')
    #     # kmi = km.keymap_items.new('foo.bar', 'B', 'PRESS')


@AddonPreferencesResrictPanels.unregister_addon
def unregister():
    restore_attributes()
    original_attributes.clear()
    new_attributes.clear()

    for cls in panel_classes:
        bpy.utils.unregister_class(cls)
    for cls in classes[::-1]:
        bpy.utils.unregister_class(cls)

    if scene_update_pre in bpy.app.handlers.scene_update_pre:
        bpy.app.handlers.scene_update_pre.remove(scene_update_pre)
    bpy.app.handlers.save_pre.remove(save_pre)
    bpy.app.handlers.save_post.remove(save_post)
    bpy.app.handlers.load_post.remove(load_post)

    bpy.app.translations.unregister(__name__)


if __name__ == '__main__':
    register()
