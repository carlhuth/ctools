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
    'version': (0, 1, 1),
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


def gen_addon_prefs_name_space():
    def key(space_type, region_type, space_context):
        # これを修正する場合は AddonPreferencesPanelRestriction.key も修正すること
        if space_type == 'PROPERTIES':
            return space_type.lower() + '_' + space_context
        else:
            return space_type.lower() + '_' + region_type.lower()

    name_space = OrderedDict()

    prop = bpy.types.Space.bl_rna.properties['type']
    space_names = {e.identifier: e.name for e in prop.enum_items}
    prop = bpy.types.Region.bl_rna.properties['type']
    region_names = {e.identifier: e.name for e in prop.enum_items}
    prop = bpy.types.SpaceProperties.bl_rna.properties['context']
    context_names = {e.identifier: e.name for e in prop.enum_items}
    for space_type, region_types in registerinfo.area_region_types.items():
        if space_type == 'EMPTY':
            continue
        if space_type == 'PROPERTIES':
            for bl_context in registerinfo.bl_context_properties:
                attr = 'use_panel_' + key(space_type, '', bl_context)
                if bl_context == 'particle':
                    ctx = 'PARTICLES'
                else:
                    ctx = bl_context.upper()
                name = '{}: {}'.format(space_names[space_type],
                                       context_names[ctx])
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
                    attr = 'use_panel_' + key(space_type, region_type, '')
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

    @classmethod
    def key(cls, space, region=None):
        # これを修正する場合は gen_addon_prefs_name_space関数の中のkey関数も
        # 修正すること
        if space.type == 'PROPERTIES':
            ctx = space.context.lower()
            if ctx == 'particles':
                ctx = 'particle'
            return space.type.lower() + '_' + ctx
        else:
            return space.type.lower() + '_' + region.type.lower()

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
    :return: {'VIEW_3D': {'TOOLS': rt, 'TOOL_PROPS': rt, ...}, ...}
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
        key = 'use_panel_' + AddonPreferencesResrictPanels.key(space, region)
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
        attr = 'restrict_' + SCREEN_PG_panel_restriction_space.key(
            space, region)
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


# def UI_panel_category_is_visible(ar):
#     categories = ar.panels_category.to_list(structures.PanelCategoryDyn)
#     return len(categories) > 1


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
        key = 'use_panel_' + AddonPreferencesResrictPanels.key(
            context.space_data, context.region)
        return getattr(addon_preferences, key)

    def draw_header(self, context):
        layout = self.layout
        wm_prop = getattr(context.window_manager,
                          SCREEN_PG_panel_restriction.WM_ATTRIBUTE)
        space = context.space_data
        region = context.region
        space_key = str(space.as_pointer())
        if space_key not in wm_prop.spaces:
            SCREEN_PG_panel_restriction.ensure_space(space)
        prop = wm_prop.spaces[space_key]
        attr = 'restrict_' + SCREEN_PG_panel_restriction_space.key(
            space, region)

        row = layout.row(align=True)
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
        cls = self.__class__

        wm_prop = getattr(context.window_manager,
                          SCREEN_PG_panel_restriction.WM_ATTRIBUTE)

        space = context.space_data
        region = context.region
        ar = structures.ARegion.cast(region)

        space_key = str(space.as_pointer())
        space_prop = wm_prop.spaces[space_key]

        context_p = context.as_pointer()
        art = all_region_types[cls.bl_space_type][cls.bl_region_type]

        active_panel_types = []
        for pt in art.paneltypes.to_list(structures.PanelType):
            panel_context = pt.context.decode('utf-8')
            if space.type == 'PROPERTIES':
                # lower()メソッドが必要な点に注意、あとperticle<>PARTICLESにも
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
                    if panel_context in registerinfo.bl_context_view3d_mode:
                        mode = registerinfo.bl_context_view3d_mode[
                            panel_context]
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
        if space.type == 'PROPERTIES':
            for pt in active_panel_types:
                row = layout.row()
                draw_item(row, pt)
        else:
            if space.type == 'VIEW_3D' and region.type == 'TOOLS':
                row = layout.row()
                row.prop(space_prop, 'show_all', text='All')
                row.prop(space_prop, 'show_mode', text='Mode')
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

        # layout.operator(SCREEN_OT_panal_restriction_move_head.bl_idname,
        #                 text='Move Head')


def generate_panel_classes():
    panel_classes.clear()

    for space_type, region_types in registerinfo.area_region_types.items():
        if space_type == 'EMPTY':
            continue
        spacetype = space_type.replace('_', '')
        for region_type in region_types:
            if space_type == 'PROPERTIES' and region_type == 'WINDOW':
                for bl_context in registerinfo.bl_context_properties:
                    name = '{}_PT_panel_restriction_{}'.format(
                        spacetype, bl_context)
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
        ctx = enum_item.identifier
        if ctx == 'PARTICLES':
            name = 'restrict_' + 'particle'
        else:
            name = 'restrict_' + ctx.lower()
        name_space[name] = bpy.props.BoolProperty(
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

    @classmethod
    def key(cls, space, region=None):
        if space.type == 'PROPERTIES':
            ctx = space.context
            if ctx == 'PARTICLES':
                return 'particle'
            else:
                return ctx.lower()
        else:
            return region.type.lower()


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
# class SCREEN_OT_panal_restriction_move_head(bpy.types.Operator):
#     bl_idname = 'screen.panal_restriction_move_head'
#     bl_label = 'Move Head'
#
#     def execute(self, context):
#         def is_generated(idname):
#             return '_panel_restriction_' in idname
#
#         for area in context.screen.areas:
#             for region in area.regions:
#                 ar = structures.ARegion.cast(region)
#                 panels = ar.panels.to_list(structures.Panel)
#                 panels.sort(key=lambda pa: pa.sortorder)
#                 self_pa = None
#                 for pa in panels:
#                     if is_generated(pa.panelname.decode('utf-8')):
#                         self_pa = pa
#                 if not self_pa:
#                     continue
#                 # self_pa.ofsy = 0
#                 # self_pa.sortorder = 0
#                 region.tag_redraw()
#
#         return {'FINISHED'}


###############################################################################
# Register, Unregister
###############################################################################
classes = [
    AddonPreferencesResrictPanels,

    # SCREEN_OT_panal_restriction_move_head,

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
