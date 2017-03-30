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


"""
# Helper class for grouping add-ons

![Image](../__images/addongroup.jpg)

# How to use

## Deploy add-ons

```
2.78/scripts/addons/my_addon/ --- __init__.py
                                 |- addongroup.py
                                 |
                                 |- foo_addon/ --- __init__.py
                                 |             |- addongroup.py
                                 |             |
                                 |             `- bar_addon/ --- __init__.py
                                 |                              `- addongroup.py
                                 |
                                 `- space_view3d_other_addon.py
```

## \_\_init\_\_.py
```
bl_info = {
    "name": "My Add-on",
    "author": "Anonymous",
    "version": (1, 0),
    "blender": (2, 78, 0),
    "location": "View3D > Tool Shelf",
    "description": "Addon group test",
    "warning": "",
    "wiki_url": "",
    "category": "3D View",
    }


if "bpy" in locals():
    import importlib
    importlib.reload(addongroup)
    MyAddonPreferences.reload_sub_modules()
else:
    from . import addongroup

import bpy


class MyAddonPreferences(
        addongroup.AddonGroupPreferences, bpy.types.AddonPreferences):
    bl_idname = __name__

    sub_modules = [
        "foo_addon",
        "space_view3d_other_addon"
    ]


classes = [
    MyAddonPreferences,
]


@MyAddonPreferences.register_addon
def register():
    for cls in classes:
        bpy.utils.register_class(cls)


@MyAddonPreferences.unregister_addon
def unregister():
    for cls in classes[::-1]:
        bpy.utils.unregister_class(cls)
```

## Fix Add-ons

If single file add-on, change it to a package and copy addongroup.py.  
If add-on does not have AddonPreferences and has no children, there is no need to modify it.

### import

From:
```
import bpy
```

To:
```
if "bpy" in locals():
    import importlib
    importlib.reload(addongroup)
    FooAddonPreferences.reload_sub_modules()
else:
    from . import addongroup

import bpy
```

### AddonPreferences

From:
```
class FooAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        ...

    @classmethod
    def register(cls):
        ...

    @classmethod
    def unregister(cls):
        ...
```

To:
```
class FooAddonPreferences(
        addongroup.AddonGroupPreferences,
        bpy.types.AddonPreferences if "." not in __name__ else
        bpy.types.PropertyGroup):
    bl_idname = __name__

    # Specify add-ons
    # If value is None instead of list, Automatically search and add
    sub_modules = [
        "bar_addon"
    ]

    def draw(self, context):
        ...
        super().draw(context)

    @classmethod
    def register(cls):
        ...
        super().register()

    @classmethod
    def unregister(cls):
        ...
        super().unregister()
```

### register and unregister functions
From:
```
def register():
    ...

def unregister():
    ...
```

To:
```
@FooAddonPreferences.register_addon
def register():
    ...

@FooAddonPreferences.unregister_addon
def unregister():
    ...
```

### bpy.utils.register_module and bpy.utils.unregister_module functions
From:
```
def register():
    bpy.utils.register_module()
    ...
    
def unregister():
    bpy.utils.unregister_module()
    ...
```

To:
```
@FooAddonPreferences.register_addon
def register():
    FooAddonPreferences.register_module()
    ...

@FooAddonPreferences.unregister_addon
def unregister():
    FooAddonPreferences.unregister_module()
    ...
```

### Instance of AddonPreferences
From:
```
addon_prefs = bpy.context.user_preferences.addons[FooAddonPreferences.bl_idname].preferences
```

To:
```
# Warning: This is not <AddonPreferences> but <PropertyGroup>
addon_prefs = FooAddonPreferences.get_instance()
```

```
# Only root add-on returns <AddonPreferences>
addon_prefs = MyAddonPreferences.get_instance()
```

### Other

```
addon_prefs = FooAddonPreferences.get_instance()

# Add-on is enabled or not
# attribute name:  use_ + module name
is_enabled = addon_prefs.use_bar_addon
if is_enabled:
    # Same as ChildAddonPreferences.get_instance()
    bar_addon_prefs = addon_prefs.bar_addon

# If this value is true the add-on details are displayed in UserPreferences
# attribute name: show_expanded_ + module name
show_bar_addon_detail = addon_prefs.show_expanded_bar_addon
```
"""


from collections import OrderedDict
import importlib
import os
import re
import sys
import traceback

import bpy


__all__ = [
    "AddonGroupPreferences",
    "register_module",
    "unregister_module"
]


class AddonGroupMiscellaneous(bpy.types.PropertyGroup):
    """For dynamically adding attributes

    Dynamically added attributes:
        fixed module name  # module.__name__.replace(".", "__")
        "use_" + fixed module name
        "show_expanded_" + fixed module name
        "_show_expanded_" + fixed module name
    """

    @classmethod
    def new_class(cls):
        return type("AddonGroupMiscellaneous",
                    (bpy.types.PropertyGroup,),
                    {})


class AddonGroupPreferences:
    """Create a hierarchical add-on.

    Dynamically added attributes:
        sub module names
        "use_" + sub module name
        "show_expanded_" + sub module name
    """

    bl_idname = ""

    sub_modules = ()
    """str list of sub modules.
    If None is specified, all files and directories included are targeted.

    Sub modules whose heads begin with _ are not displayed in UserPreference
    by default. They are displayed when enable the 'Show Hidden' option.

    :type: list[str]
    """

    _fake_sub_modules = OrderedDict()

    # misc_ = bpy.props.PointerProperty(
    #     type=AddonGroupMiscellaneous.new_class())
    misc_ = None

    align_box_draw_ = bpy.props.BoolProperty(
        name="Box Draw",
        description="If applied patch: patch/ui_layout_box.patch",
        default=False)
    use_indent_draw_ = bpy.props.BoolProperty(
        name="Indent",
        default=True)
    show_hidden_ = bpy.props.BoolProperty(
        name="Show Hidden",
        default=False)

    _addon_filter_items = None  # cache for dynamic enum items

    def _prop_addon_filter_items(self, context):
        items = [('All', "All", "All Add-ons"),
                 ('Enabled', "Enabled", "All Enabled Add-ons"),
                 ('Disabled', "Disabled", "All Disabled Add-ons"),
                 ]

        items_unique = set()

        for mod_name, fake_mod in self._fake_sub_modules.items():
            info = fake_mod.bl_info
            items_unique.add(info["category"])

        items.extend([(cat, cat, "") for cat in sorted(items_unique)])
        self.__class__._addon_filter_items = items
        return items

    def _prop_addon_search_get(self):
        return getattr(self, "addon_search__", "")

    def _prop_addon_search_set(self, value):
        setattr(self.__class__, "addon_search__", value)

    def _prop_addon_filter_get(self):
        return getattr(self, "addon_filter__", 0)

    def _prop_addon_filter_set(self, value):
        setattr(self.__class__, "addon_filter__", value)

    addon_search_ = bpy.props.StringProperty(
        name="Search",
        description="Search within the selected filter. "
                    "If startswith \"/\"/, use path search ",
        options={'TEXTEDIT_UPDATE'},
        get=_prop_addon_search_get,
        set=_prop_addon_search_set,
    )
    addon_filter_ = bpy.props.EnumProperty(
        items=_prop_addon_filter_items,
        name="Category",
        description="Filter add-ons by category",
        get=_prop_addon_filter_get,
        set=_prop_addon_filter_set,
    )

    del _prop_addon_filter_items
    del _prop_addon_search_get, _prop_addon_search_set
    del _prop_addon_filter_get, _prop_addon_filter_set

    def __getattribute__(self, name):
        prefix, base = re.match("(use_|show_expanded_|)(.*)", name).groups()
        if base in super().__getattribute__("_fake_sub_modules"):
            misc = super().__getattribute__("misc_")
            attr = prefix + self.__mod_to_attr(self._fake_sub_modules[base])
            return getattr(misc, attr)
        else:
            return super().__getattribute__(name)

    def __setattr__(self, name, value):
        def is_bpy_props(val):
            """return True if argument:val is in a format such as
            (bpy.props.BoolProperty, {name="Name", default="True"})
            """
            try:
                t, kwargs = val
                props = [getattr(bpy.props, attr) for attr in dir(bpy.props)]
                return t in props and isinstance(kwargs, dict)
            except:
                return False

        prefix, base = re.match("(use_|show_expanded_|)(.*)", name).groups()
        if base in self._fake_sub_modules:
            misc = self.misc_
            attr = prefix + self.__mod_to_attr(self._fake_sub_modules[base])
            if is_bpy_props(value):
                setattr(misc.__class__, attr, value)
            else:
                setattr(misc, attr, value)
        else:
            super().__setattr__(name, value)

    def __delattr__(self, name):
        prefix, base = re.match("(use_|show_expanded_|)(.*)", name).groups()
        if base in self._fake_sub_modules:
            misc = self.misc_
            attr = prefix + self.__mod_to_attr(self._fake_sub_modules[base])
            delattr(misc.__class__, attr)
        else:
            super().__delattr__(name)

    def __dir__(self):
        attrs = list(super().__dir__())
        misc = self.misc_
        for name in self._fake_sub_modules:
            attr = self.__mod_to_attr(self._fake_sub_modules[name])
            for pre in ("", "use_", "show_expanded_"):
                n = pre + attr
                if hasattr(misc, n):
                    attrs.append(pre + name)
        return attrs

    @classmethod
    def __get_misc_type(cls):
        return cls.misc_[1]["type"]

    @classmethod
    def reload_sub_modules(cls):
        """
        e.g.
        if "bpy" in locals():
            import importlib
            AddonGroupPreferences.reload_sub_modules()
        """
        if cls.is_registered:
            cls.__unregister_sub_modules()
            cls.__free_attributes()

        cls.__free_fake_sub_modules()
        cls.__init_fake_sub_modules()
        for fake_mod in cls._fake_sub_modules.values():
            try:
                if fake_mod.__name__ in sys.modules:
                    mod = importlib.import_module(fake_mod.__name__)
                    # print("Reloading:", mod)
                    importlib.reload(mod)
            except:
                traceback.print_exc()

        if cls.is_registered:
            cls.__init_attributes()
            cls.__register_sub_modules()

    _get_instance_cache = None

    @classmethod
    def get_instance(cls):
        """return instance
        :rtype: AddonPreferences
        """
        if cls._get_instance_cache:
            return cls._get_instance_cache

        U = bpy.context.user_preferences
        attrs = cls.bl_idname.split(".")
        if attrs[0] not in U.addons:  # wm.read_factory_settings()
            return None
        prefs = U.addons[attrs[0]].preferences
        for attr in attrs[1:]:
            if not hasattr(prefs, attr):
                return None
            prefs = getattr(prefs, attr)
        cls._get_instance_cache = prefs
        return prefs

    @staticmethod
    def __mod_to_attr(mod):
        return mod.__name__.replace(".", "__")

    @classmethod
    def __fake_module(cls, mod_name, mod_path, speedy=True, force_support=None,
                      quiet=True):
        """source: scripts/modules/addon_utils.py: module_refresh()
        fix it not to use error_encoding. add "quiet" argument
        """
        if 0:
            global error_encoding

        if bpy.app.debug_python:
            print("fake_module", mod_path, mod_name)
        import ast
        ModuleType = type(ast)
        try:
            file_mod = open(mod_path, "r", encoding="UTF-8")
        except OSError as e:
            print("Error opening file %r: %s" % (mod_path, e))
            return None

        with file_mod:
            if speedy:
                lines = []
                line_iter = iter(file_mod)
                l = ""
                while not l.startswith("bl_info"):
                    try:
                        l = line_iter.readline()
                    except UnicodeDecodeError as e:
                        if 0:
                            if not error_encoding:
                                error_encoding = True
                                print("Error reading file as UTF-8:", mod_path,
                                      e)
                        else:
                            print("Error reading file as UTF-8:", mod_path, e)
                        return None

                    if len(l) == 0:
                        break
                while l.rstrip():
                    lines.append(l)
                    try:
                        l = line_iter.readline()
                    except UnicodeDecodeError as e:
                        if 0:
                            if not error_encoding:
                                error_encoding = True
                                print("Error reading file as UTF-8:", mod_path,
                                      e)
                        else:
                            print("Error reading file as UTF-8:", mod_path, e)
                        return None

                data = "".join(lines)

            else:
                data = file_mod.read()
        del file_mod

        try:
            ast_data = ast.parse(data, filename=mod_path)
        except:
            print("Syntax error 'ast.parse' can't read %r" % mod_path)
            import traceback
            traceback.print_exc()
            ast_data = None

        body_info = None

        if ast_data:
            for body in ast_data.body:
                if body.__class__ == ast.Assign:
                    if len(body.targets) == 1:
                        if getattr(body.targets[0], "id", "") == "bl_info":
                            body_info = body
                            break

        if body_info:
            try:
                mod = ModuleType(mod_name)
                mod.bl_info = ast.literal_eval(body.value)
                mod.__file__ = mod_path
                mod.__time__ = os.path.getmtime(mod_path)
            except:
                print("AST error parsing bl_info for %s" % mod_name)
                import traceback
                traceback.print_exc()
                raise

            if force_support is not None:
                mod.bl_info["support"] = force_support

            return mod
        else:
            if not quiet:
                print("fake_module: addon missing 'bl_info' "
                      "gives bad performance!: %r" % mod_path)
            return None

    @classmethod
    def __generate_fake_sub_modules(cls):
        # genarate cls._face_modules
        fake_modules = []
        mod = sys.modules[cls.bl_idname]
        if os.path.basename(mod.__file__) != "__init__.py":
            # TODO: zip file
            return OrderedDict()
        addon_dir = os.path.dirname(mod.__file__)
        module_names = bpy.path.module_names(addon_dir)

        def sort_func(item):
            name, path = item
            if cls.sub_modules is not None:
                if name in cls.sub_modules:
                    return cls.sub_modules.index(name)
                else:
                    return len(cls.sub_modules) + module_names.index(item)
            else:
                return module_names.index(item)

        for mod_name, mod_path in sorted(module_names, key=sort_func):
            # Skip same files and undesignated modules.
            if os.path.realpath(mod_path) == os.path.realpath(__file__):
                continue
            else:
                # check hard link and symbolic link. only unix and windows
                try:
                    if os.path.samefile(mod_path, __file__):
                        continue
                except:
                    pass
            if cls.sub_modules is not None:
                if mod_name not in cls.sub_modules:
                    continue

            mod = cls._fake_sub_modules.get(mod_name)
            if mod:
                if mod.__time__ != os.path.getmtime(mod_path):
                    print("reloading addon:",
                          mod.__name__,
                          mod.__time__,
                          os.path.getmtime(mod_path),
                          mod_path,
                          )
            mod = cls.__fake_module(cls.bl_idname + "." + mod_name, mod_path)
            if mod:
                fake_modules.append(mod)

        fake_modules.sort(
            key=lambda mod: (mod.bl_info["category"], mod.bl_info["name"]))
        fake_modules = OrderedDict(
            [(mod.__name__.split(".")[-1], mod) for mod in fake_modules])

        if cls.sub_modules is not None:
            for name in cls.sub_modules:
                if name not in fake_modules:
                    print("Submodule not found: {}.{}".format(
                        cls.bl_idname, name))
        return fake_modules

    @classmethod
    def __init_fake_sub_modules(cls):
        cls._fake_sub_modules = cls.__generate_fake_sub_modules()

    @classmethod
    def __free_fake_sub_modules(cls):
        cls._fake_sub_modules.clear()

    @classmethod
    def __init_attributes(cls):
        prefs = cls.get_instance()
        misc_type = cls.__get_misc_type()

        for name, fake_mod in cls._fake_sub_modules.items():
            info = fake_mod.bl_info

            def gen_update(fake_mod):
                def update(self, context):
                    name_attr = cls.__mod_to_attr(fake_mod)
                    try:
                        mod = importlib.import_module(fake_mod.__name__)
                        if getattr(self, "use_" + name_attr):
                            cls.__register_sub_module(mod)
                        else:
                            cls.__unregister_sub_module(mod, True)
                    except:
                        traceback.print_exc()
                return update

            prop = bpy.props.BoolProperty(
                name=info["name"],
                description=info.get("description", "").rstrip("."),
                update=gen_update(fake_mod),
            )
            setattr(prefs, "use_" + name, prop)

            def gen_func(fake_mod):
                attr = cls.__mod_to_attr(fake_mod)

                def fget(self):
                    return getattr(misc_type, "_show_expanded_" + attr, False)

                def fset(self, value):
                    setattr(misc_type, "_show_expanded_" + attr, value)

                return fget, fset

            fget, fset = gen_func(fake_mod)
            prop = bpy.props.BoolProperty(get=fget, set=fset)
            setattr(prefs, "show_expanded_" + name, prop)

    @classmethod
    def __free_attributes(cls):
        prefs = cls.get_instance()
        misc_type = cls.__get_misc_type()
        for name, fake_mod in cls._fake_sub_modules.items():
            delattr(prefs, "use_" + name)
            delattr(prefs, "show_expanded_" + name)
            attr = cls.__mod_to_attr(fake_mod)
            if hasattr(misc_type, "_show_expanded_" + attr):
                delattr(misc_type, "_show_expanded_" + attr)

    @classmethod
    def __register_sub_module(cls, mod):
        if not hasattr(mod, "__addon_enabled__"):
            mod.__addon_enabled__ = False
        if not mod.__addon_enabled__:
            mod.register()
            mod.__addon_enabled__ = True

    @classmethod
    def __register_sub_modules(cls):
        prefs = cls.get_instance()
        for name, fake_mod in cls._fake_sub_modules.items():
            if getattr(prefs, "use_" + name):
                try:
                    mod = importlib.import_module(fake_mod.__name__)
                    cls.__register_sub_module(mod)
                except:
                    setattr(prefs, "use_" + name, False)
                    traceback.print_exc()

    @classmethod
    def __unregister_sub_module(cls, mod, clear_preferences=False):
        if not hasattr(mod, "__addon_enabled__"):
            mod.__addon_enabled__ = False
        if mod.__addon_enabled__:
            mod.unregister()
            mod.__addon_enabled__ = False

        if clear_preferences:
            prefs = cls.get_instance()
            for prefix in ("", "use_", "show_expanded_"):
                attr = prefix + cls.__mod_to_attr(mod)
                if attr in prefs.misc_:
                    del prefs.misc_[attr]

    @classmethod
    def __unregister_sub_modules(cls):
        prefs = cls.get_instance()
        for name, fake_mod in cls._fake_sub_modules.items():
            if getattr(prefs, "use_" + name):
                try:
                    mod = importlib.import_module(fake_mod.__name__)
                    cls.__unregister_sub_module(mod)
                except:
                    traceback.print_exc()

    @classmethod
    def register(cls):
        cls._get_instance_cache = None

        if "." in cls.bl_idname:  # set property to parent
            U = bpy.context.user_preferences
            attrs = cls.bl_idname.split(".")
            base_prop = U.addons[attrs[0]].preferences
            for attr in attrs[1:-1]:
                base_prop = getattr(base_prop, attr)
            prop = bpy.props.PointerProperty(type=cls)
            setattr(base_prop, attrs[-1], prop)

        cls.__init_fake_sub_modules()
        cls.__init_attributes()
        cls.__register_sub_modules()

        c = super()
        if hasattr(c, "register"):
            c.register()

    @classmethod
    def unregister(cls):
        U = bpy.context.user_preferences
        attrs = cls.bl_idname.split(".")
        if attrs[0] not in U.addons:  # wm.read_factory_settings()
            return None

        cls.__unregister_sub_modules()
        cls.__free_attributes()
        cls.__free_fake_sub_modules()

        if "." in cls.bl_idname:  # remove from parent
            base_prop = U.addons[attrs[0]].preferences
            for attr in attrs[1:-1]:
                base_prop = getattr(base_prop, attr)
            delattr(base_prop, attrs[-1])

        c = super()
        if hasattr(c, "unregister"):
            c.unregister()

        cls._get_instance_cache = None

    @classmethod
    def register_addon(cls, func, **kwargs):
        """decorator fro addon register function.

        e.g.
        @AddonGroupPreferences.register_addon
        def register():
            ...
        """
        import functools

        @functools.wraps(func)
        def new_func():
            misc_type = AddonGroupMiscellaneous.new_class()
            bpy.utils.register_class(misc_type)
            cls.misc_ = bpy.props.PointerProperty(type=misc_type)
            func()
        new_func._register = func

        c = super()
        if hasattr(c, "register_addon"):
            new_func = c.register_addon(new_func, **kwargs)

        return new_func

    @classmethod
    def unregister_addon(cls, func, **kwargs):
        """decorator for addon unregister function.

        e.g.
        @AddonGroupPreferences.unregister_addon
        def unregister():
            ...
        """
        import functools

        @functools.wraps(func)
        def new_func():
            misc_type = cls.__get_misc_type()
            # if misc_type.is_registered:
            bpy.utils.unregister_class(misc_type)
            func()

        new_func._unregister = func

        c = super()
        if hasattr(c, "unregister_addon"):
            new_func = c.unregister_addon(new_func, **kwargs)

        return new_func

    def draw(self, context, **kwargs):
        """
        :type context: bpy.types.Context
        """
        layout = self.layout
        """:type: bpy.types.UILayout"""

        bl_idname = self.__class__.bl_idname

        if "." not in bl_idname:
            align_box_draw = self.align_box_draw_
            use_indent_draw = self.use_indent_draw_
        else:
            U = context.user_preferences
            root_prefs = U.addons[bl_idname.split(".")[0]].preferences
            align_box_draw = root_prefs.align_box_draw_
            use_indent_draw = root_prefs.use_indent_draw_

        if self._fake_sub_modules:
            split = layout.split()
            col = split.column()
            sp = col.split(0.8)
            row = sp.row()
            row.prop(self, "addon_search_", text="", icon='VIEWZOOM')
            sp.row()
            col = split.column()
            sp = col.split(0.8)
            row = sp.row()
            row.prop(self, "addon_filter_")
            sp.row()

        filter = self.addon_filter_
        search = self.addon_search_

        for mod_name, fake_mod in self._fake_sub_modules.items():
            if not self.show_hidden_ and mod_name.startswith("_"):
                continue

            mod_name_attr = self.__mod_to_attr(fake_mod)
            info = fake_mod.bl_info

            is_enabled = getattr(self, "use_" + mod_name)
            if ((filter == 'All') or
                    (filter == info["category"]) or
                    (filter == 'Enabled' and is_enabled) or
                    (filter == 'Disabled' and not is_enabled)):
                pass
            else:
                continue

            if search:
                if search.startswith("//"):
                    if re.search(search.lstrip("//"), fake_mod.__file__):
                        match = True
                    else:
                        match = False
                else:
                    match = True
                    for word in search.split(" "):
                        if not word:
                            continue
                        if word.lower() in info["name"].lower():
                            pass
                        elif (info["author"] and
                              word.lower() in info["author"].lower()):
                            pass
                        else:
                            match = False
                            break
                if not match:
                    continue

            column = layout.column(align=align_box_draw)

            # Indend
            if use_indent_draw:
                sp = column.split(0.01)
                sp.column()
                column = sp.column(align=align_box_draw)

            box = column.box()

            # Title
            expand = getattr(self, "show_expanded_" + mod_name)
            icon = 'TRIA_DOWN' if expand else 'TRIA_RIGHT'
            col = box.column()  # boxのままだと行間が広い
            row = col.row()
            sub = row.row()
            sub.context_pointer_set("addon_prefs", self)
            sub.alignment = 'LEFT'
            op = sub.operator("wm.context_toggle", text="", icon=icon,
                              emboss=False)
            op.data_path = "addon_prefs.show_expanded_" + mod_name
            sub = row.row()
            sub.label("{}: {}".format(info["category"], info["name"]))
            sub = row.row()
            sub.alignment = 'RIGHT'
            if mod_name.startswith("_"):
                sub.label("", icon='SCRIPTPLUGINS')
            if info.get("warning"):
                sub.label("", icon='ERROR')
            sub.prop(self.misc_, "use_" + mod_name_attr, text="")

            # Info
            if expand:
                # reference: space_userpref.py
                if info.get("description"):
                    split = col.row().split(percentage=0.15)
                    split.label("Description:")
                    split.label(info["description"])
                if info.get("location"):
                    split = col.row().split(percentage=0.15)
                    split.label("Location:")
                    split.label(info["location"])
                split = col.row().split(percentage=0.15)
                split.label("File:")
                split.label(fake_mod.__file__)
                if info.get("author"):
                    mod = sys.modules[bl_idname]
                    base_info = getattr(mod, "bl_info", None)
                    if not isinstance(base_info, dict):
                        base_info = {}
                    if info["author"] != base_info.get("author"):
                        split = col.row().split(percentage=0.15)
                        split.label("Author:")
                        split.label(info["author"])
                if info.get("version"):
                    split = col.row().split(percentage=0.15)
                    split.label("Version:")
                    split.label(".".join(str(x) for x in info["version"]),
                                translate=False)
                if info.get("warning"):
                    split = col.row().split(percentage=0.15)
                    split.label("Warning:")
                    split.label("  " + info["warning"], icon="ERROR")

                tot_row = int(bool(info.get("wiki_url")))
                if tot_row:
                    split = col.row().split(percentage=0.15)
                    split.label(text="Internet:")
                    if info.get("wiki_url"):
                        op = split.operator("wm.url_open",
                                            text="Documentation", icon="HELP")
                        op.url = info.get("wiki_url")
                    for i in range(4 - tot_row):
                        split.separator()

                # Preferences
                if getattr(self, "use_" + mod_name):
                    try:
                        prefs = getattr(self, mod_name, None)
                    except:
                        traceback.print_exc()
                        continue
                    if prefs and hasattr(prefs, "draw"):
                        if align_box_draw:
                            col = column.box().column()
                        else:
                            col = box.column()

                        col_head = col.column()
                        col_body = col.column()
                        prefs.layout = col_body
                        has_error = False
                        try:
                            prefs.draw(context)
                        except:
                            traceback.print_exc()
                            has_error = True
                        has_introspect_error = False
                        try:
                            # SyntaxError may occur due to " or "
                            introspect = eval(col_body.introspect())
                        except:
                            # traceback.print_exc()
                            has_introspect_error = True
                        if has_introspect_error or introspect[0] or has_error:
                            if not align_box_draw:
                                sub = col_head.row()
                                sub.active = False  # To make the color thinner
                                sub.label("―" * 40)
                            col_head.label("Preferences:")
                        if has_error:
                            col_body.label(text="Error (see console)",
                                           icon='ERROR')
                        del prefs.layout

        if "." not in bl_idname and self._fake_sub_modules:
            row = layout.row()
            sub = row.row()
            sub.alignment = 'LEFT'
            sub.prop(self, "show_hidden_")
            sub = row.row()
            sub.alignment = 'RIGHT'
            sub.prop(self, "align_box_draw_")
            sub.prop(self, "use_indent_draw_")

        c = super()
        if hasattr(c, "draw"):
            c.draw(context, **kwargs)

    @classmethod
    def register_module(cls, module=None, verbose=False):
        """Modified bpy.utils.register_module()
        :type module: str
        :type verbose: bool
        """
        if module:
            if cls.bl_idname and module != cls.bl_idname:
                msg = "Can not specify another module: must {}, got {}"
                msg = msg.format(cls.bl_idname, module)
                raise ValueError(msg)
        else:
            module = cls.bl_idname
        if verbose:
            print("bpy.utils.register_module(%r): ..." % module)
        root_module = module.split(".")[0]
        if cls.bl_idname:
            fake_modules = cls.__generate_fake_sub_modules()
        else:
            fake_modules = None
        cls_ = None
        for cls_ in bpy.utils._bpy_module_classes(root_module,
                                                  is_registered=False):
            if not cls_.__module__.startswith(module):
                continue
            if fake_modules is not None:
                is_submodule = False
                for m in fake_modules:
                    if cls_.__module__.startswith(module + "." + m):
                        is_submodule = True
                        break
                if is_submodule:
                    continue

            if verbose:
                print("    %r" % cls_)
            try:
                bpy.utils.register_class(cls_)
            except:
                print("bpy.utils.register_module(): "
                      "failed to registering class %r" % cls_)
                import traceback
                traceback.print_exc()
        if verbose:
            print("done.\n")
        if cls_ is None:
            raise Exception("register_module(%r): defines no classes" % module)

    @classmethod
    def unregister_module(cls, module=None, verbose=False):
        """Modified bpy.utils.unregister_module()
        :type module: str
        :type verbose: bool
        """
        if module:
            if cls.bl_idname and module != cls.bl_idname:
                msg = "Can not specify another module: must {}, got {}"
                msg = msg.format(cls.bl_idname, module)
                raise ValueError(msg)
        else:
            module = cls.bl_idname
        if verbose:
            print("bpy.utils.unregister_module(%r): ..." % module)
        root_module = module.split(".")[0]
        if cls.bl_idname:
            fake_modules = cls.__generate_fake_sub_modules()
        else:
            fake_modules = None
        for cls_ in bpy.utils._bpy_module_classes(root_module,
                                                  is_registered=True):
            if not cls_.__module__.startswith(module):
                continue
            if fake_modules is not None:
                is_submodule = False
                for m in fake_modules:
                    if cls_.__module__.startswith(module + "." + m):
                        is_submodule = True
                        break
                if is_submodule:
                    continue

            if verbose:
                print("    %r" % cls_)
            try:
                bpy.utils.unregister_class(cls_)
            except:
                print("bpy.utils.unregister_module(): "
                      "failed to unregistering class %r" % cls_)
                import traceback
                traceback.print_exc()
        if verbose:
            print("done.\n")


def register_module(module, verbose=False):
    """Modified bpy.utils.register_module()
    :type module: str
    :type verbose: bool
    """
    AddonGroupPreferences.register_module(module, verbose)


def unregister_module(module, verbose=False):
    """Modified bpy.utils.unregister_module()
    :type module: str
    :type verbose: bool
    """
    AddonGroupPreferences.unregister_module(module, verbose)
