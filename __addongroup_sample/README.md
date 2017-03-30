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