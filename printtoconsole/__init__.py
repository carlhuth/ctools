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
    'name': 'Print to Console',
    'author': 'chromoly',
    'version': (0, 2, 3),
    'blender': (2, 78, 0),
    'location': 'Python Console',
    'description': 'print() -> Python Console',
    'warning': '',
    'wiki_url': '',
    'tracker_url': '',
    'category': 'System',
}


"""
pythonの標準出力と標準エラーをPythonConsoleにも出力する
"""


import importlib
import io
import sys

import bpy

try:
    importlib.reload(addongroup)
    importlib.reload(registerinfo)
except NameError:
    from ..utils import addongroup
    from ..utils import registerinfo


class PrintToConsolePreferences(
        addongroup.AddonGroupPreferences,
        registerinfo.AddonRegisterInfo,
        bpy.types.PropertyGroup if '.' in __name__ else
        bpy.types.AddonPreferences):
    bl_idname = __name__


stdout = stderr = None


class Out(io.StringIO):
    output_type = 'stdout'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buf = ''

    def get_context(self):
        for area in bpy.context.screen.areas:
            if area.type == 'CONSOLE':
                break
        else:
            return None
        ctx = bpy.context.copy()
        ctx['area'] = area
        return ctx

    def write(self, text, flush=False):
        if self.output_type == 'stdout':
            stdout.write(text)
            scrollback_type = 'OUTPUT'
        else:
            stderr.write(text)
            scrollback_type = 'ERROR'

        ctx = self.get_context()
        if not ctx:
            return

        self.buf += text
        if self.buf and '\n' in self.buf:
            lines = self.buf.split('\n')
            for line in lines[:-1]:
                bpy.ops.console.scrollback_append(ctx, text=line,
                                                  type=scrollback_type)
            self.buf = lines[-1]
        if flush and self.buf:
            bpy.ops.console.scrollback_append(ctx, text=self.buf,
                                              type=scrollback_type)
            self.buf = ''

    def flush(self):
        self.write('', flush=True)


class Err(Out):
    output_type = 'stderr'


classes = [PrintToConsolePreferences]


@PrintToConsolePreferences.register_addon
def register():
    global stdout, stderr
    for cls in classes:
        bpy.utils.register_class(cls)
    stdout = sys.stdout
    stderr = sys.stderr
    sys.stdout = Out()
    sys.stderr = Err()


@PrintToConsolePreferences.unregister_addon
def unregister():
    for cls in classes[::-1]:
        bpy.utils.unregister_class(cls)
    sys.stdout = stdout
    sys.stderr = stderr


if __name__ == '__main__':
    register()
