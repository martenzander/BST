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

# <pep8-80 compliant>
import os

import bpy
import bl_app_override

from bl_app_override.helpers import AppOverrideState
from bpy.app.handlers import persistent


class AppStateStore(AppOverrideState):
    # Just provides data & callbacks for AppOverrideState
    __slots__ = ()

    @staticmethod
    def class_ignore():
        classes = []

        # I found I actually only need to override a couple of headers
        # and then the media-viewer already looks like it needs to look.
        # I had troubles using this:

        # cls = bl_app_override.class_filter(
        #         bpy.types.Header,
        #         blacklist={"TOPBAR_HT_upper_bar", "..."}
        #     ),

        # As this made it impossible to append a new draw handler after that
        # to the headers....

        # Mr. Hackerman.
        # Overrides draw function of header to just return None
        # That way we clear all these header globally and can replace
        # them with our custom draw function
        bpy.types.TOPBAR_HT_upper_bar.draw = lambda self, context: None
        bpy.types.STATUSBAR_HT_header.draw = lambda self, context: None
        bpy.types.IMAGE_HT_header.draw = lambda self, context: None
        bpy.types.SEQUENCER_HT_header.draw = lambda self, context: None
        bpy.types.TEXT_HT_header.draw = lambda self, context: None

        return classes

    # ----------------
    # UI Filter/Ignore

    @staticmethod
    def ui_ignore_classes():
        # What does this do?
        return ()

    @staticmethod
    def ui_ignore_operator(op_id):
        return True

    @staticmethod
    def ui_ignore_property(ty, prop):
        return True

    @staticmethod
    def ui_ignore_menu(menu_id):
        return True

    @staticmethod
    def ui_ignore_label(text):
        return True

    # -------
    # Add-ons

    @staticmethod
    def addon_paths():
        return (os.path.normpath(os.path.join(os.path.dirname(__file__), "addons")),)

    @staticmethod
    def addons():
        return ("media_viewer",)


@persistent
def handler_load_recent_directory(_):
    bpy.ops.media_viewer.load_recent_directory()


@persistent
def handler_set_template_defaults(_):
    bpy.ops.media_viewer.set_template_defaults()


app_state = AppStateStore()


def register():
    print("Template Register", __file__)
    app_state.setup()

    # Handler.
    bpy.app.handlers.load_post.append(handler_load_recent_directory)
    bpy.app.handlers.load_post.append(handler_set_template_defaults)


def unregister():
    print("Template Unregister", __file__)
    app_state.teardown()

    # Handler.
    bpy.app.handlers.load_post.remove(handler_load_recent_directory)
    bpy.app.handlers.load_post.remove(handler_set_template_defaults)
