# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# ***** END GPL LICENCE BLOCK *****
#
# (c) 2022, Blender Foundation - Demeter Dzadik

from typing import List, Dict, Union, Any, Set, Optional, Tuple
from pathlib import Path
from datetime import datetime

import bpy
from bpy.props import IntProperty, StringProperty, CollectionProperty, BoolProperty, EnumProperty
from .util import get_addon_prefs, make_getter_func, make_setter_func_readonly
from . import svn_status

from .ops import SVN_Operator_Single_File
from .prefs import get_visible_indicies

class SVN_file(bpy.types.PropertyGroup):
    """Property Group that can represent a version of a File in an SVN repository."""

    name: StringProperty(
        name="File Name",
        get=make_getter_func("name", ""),
        set=make_setter_func_readonly("name"),
    )
    svn_path: StringProperty(
        name = "SVN Path",
        description="Filepath relative to the SVN root",
        get=make_getter_func("svn_path", ""),
        set=make_setter_func_readonly("svn_path"),
    )
    status: EnumProperty(
        name="Status",
        items=svn_status.ENUM_SVN_STATUS,
        default="normal",
    )
    revision: IntProperty(
        name="Revision",
        description="Revision number",
    )
    is_referenced: BoolProperty(
        name="Is Referenced",
        description="True when this file is referenced by this .blend file either directly or indirectly. Flag used for list filtering",
        default=False,
    )


    @property
    def status_icon(self) -> str:
        return svn_status.SVN_STATUS_DATA[self.status][0]

    @property
    def status_name(self) -> str:
        if self.status == 'none':
            return 'Outdated'
        return self.status.title()


class SVN_log(bpy.types.PropertyGroup):
    """Property Group that can represent an SVN log entry."""

    revision_number: IntProperty(
        name="Revision Number",
        description="Revision number of the current .blend file",
        get = make_getter_func("revision_number", 0),
        set = make_setter_func_readonly("revision_number")
    )
    revision_date: StringProperty(
        name="Revision Date",
        description="Date when the current revision was committed",
        get = make_getter_func("revision_date", ""),
        set = make_setter_func_readonly("revision_date")
    )
    revision_author: StringProperty(
        name="Revision Author",
        description="SVN username of the revision author",
        get = make_getter_func("revision_author", ""),
        set = make_setter_func_readonly("revision_author")
    )
    commit_message: StringProperty(
        name = "Commit Message",
        description="Commit message written by the commit author to describe the changes in this revision",
        get = make_getter_func("commit_message", ""),
        set = make_setter_func_readonly("commit_message")
    )

    changed_files: CollectionProperty(
        type = SVN_file,
        name = "Changed Files",
        description = "List of file paths relative to the SVN root that were affected by this revision"
    )


def layout_log_split(layout):
    main = layout.split(factor=0.4)
    num_and_auth = main.row()
    date_and_msg = main.row()
    
    num_and_auth_split = num_and_auth.split(factor=0.3)
    num = num_and_auth_split.row()
    auth = num_and_auth_split.row()

    date_and_msg_split = date_and_msg.split(factor=0.3)
    date = date_and_msg_split.row()
    msg = date_and_msg_split.row()

    return num, auth, date, msg


class SVN_UL_log(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type != 'DEFAULT':
            raise NotImplemented
        
        log_entry = item

        num, auth, date, msg = layout_log_split(layout.row())

        active_file = context.scene.svn.external_files[context.scene.svn.external_files_active_index]
        if item.revision_number == active_file.revision:
            num.label(text=str(log_entry.revision_number), icon='LAYER_ACTIVE')
        else:
            num.label(text=str(log_entry.revision_number))
        auth.label(text=log_entry.revision_author)
        date.label(text=log_entry.revision_date.split(" ")[0][5:])

        commit_msg = log_entry.commit_message
        commit_msg = commit_msg.split("\n")[0] if "\n" in commit_msg else commit_msg
        # commit_msg = commit_msg[:30]+"..." if len(commit_msg) > 32 else commit_msg
        msg.alignment = 'LEFT'
        msg.operator("svn.display_commit_message", text=commit_msg, emboss=False).log_rev=log_entry.revision_number

    def filter_items(self, context, data, propname):
        """Default filtering functionality:
            - Filter by name
            - Invert filter
            - Sort alphabetical by name
        """
        flt_flags = []
        flt_neworder = []
        list_items = getattr(data, propname)

        helper_funcs = bpy.types.UI_UL_list

        # if self.use_filter_sort_alpha:
        #     flt_neworder = helper_funcs.sort_items_by_name(list_items, "name")

        # if self.filter_name:
        #     flt_flags = helper_funcs.filter_items_by_name(self.filter_name, self.bitflag_filter_item, list_items, "name",
        #                                                     reverse=self.use_filter_sort_reverse)

        if not flt_flags:
            # Start off with all entries being filtered out.
            flt_flags = [0] * len(list_items)

        svn = context.scene.svn
        active_file = svn.external_files[svn.external_files_active_index]
        for idx, log_entry in enumerate(svn.log):
            for affected_file in log_entry.changed_files:
                if affected_file.svn_path == "/"+active_file.svn_path:
                    # If the active file is one of the files affected by this log
                    # entry, show it in the list.
                    flt_flags[idx] = self.bitflag_filter_item
                    break
    
        return flt_flags, flt_neworder


class VIEW3D_PT_svn_log(bpy.types.Panel):
    """Display the revision history of the selected file."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SVN'
    bl_label = 'Revision History'
    bl_parent_id = "VIEW3D_PT_svn_files"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return get_visible_indicies(context)
            

    def draw(self, context):
        # TODO: SVN log only makes sense for files with certain statuses (eg., not "Unversioned")
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        num, auth, date, msg = layout_log_split(layout.row())
        num.label(text="r#")
        auth.label(text="Author")
        date.label(text="Date")
        msg.label(text="Message")
        layout.template_list(
            "SVN_UL_log",
            "svn_log",
            context.scene.svn,
            "log",
            context.scene.svn,
            "log_active_index",
        )

        active_log = context.scene.svn.log[context.scene.svn.log_active_index]
        col = layout.column(align=True)
        col.prop(active_log, 'revision_number', emboss=False)
        col.prop(active_log, 'revision_date', emboss=False)
        col.prop(active_log, 'revision_author', emboss=False)


def read_svn_log_file(context, filepath: Path):
    """Read the svn.log file (written by this addon) into the log entry list."""

    svn = context.scene.svn
    svn.log.clear()

    # Read file into lists of lines where each list is one log entry
    chunks = []
    if not filepath.exists():
        # Nothing to read!
        return
    with open(filepath, 'r') as f:
        next(f)
        chunk = []
        for line in f:
            line = line.replace("\n", "")
            if len(line) == 0:
                continue
            if line == "-" * 72:
                # The previous log entry is over.
                chunks.append(chunk)
                chunk = []
                continue
            chunk.append(line)

    previous_rev_number = 0
    for chunk in chunks:
        # Read the first line of the svn log containing revision number, author,
        # date and commit message length.
        r_number, r_author, r_date, r_msg_length = chunk[0].split(" | ")
        r_number = int(r_number[1:])
        assert r_number == previous_rev_number+1, f"Revision order seems wrong at r{r_number}"
        previous_rev_number = r_number

        r_msg_length = int(r_msg_length.split(" ")[0])
        date, time, _timezone, _day, _n_day, _mo, _y = r_date.split(" ")

        log_entry = svn.log.add()
        log_entry['revision_number'] = r_number
        log_entry['revision_author'] = r_author

        rev_datetime = datetime.strptime(f"{date} {time}", '%Y-%m-%d %H:%M:%S')
        month_name = rev_datetime.strftime("%b")
        date_str = f"{rev_datetime.year}-{month_name}-{rev_datetime.day}"
        time_str = f"{str(rev_datetime.hour).zfill(2)}:{str(rev_datetime.minute).zfill(2)}"

        log_entry['revision_date'] = date_str + " " + time_str

        # File change set is on line 3 until the commit message begins...
        file_change_lines = chunk[2:-r_msg_length]
        for line in file_change_lines:
            status_char = line[3]
            file_path = line[5:]

            log_file_entry = log_entry.changed_files.add()
            log_file_entry['svn_path'] = file_path
            log_file_entry['revision'] = r_number
            log_file_entry['name'] = Path(file_path).name
            log_file_entry.status = svn_status.SVN_STATUS_CHAR[status_char]

        log_entry['commit_message'] = "\n".join(chunk[-r_msg_length:])


class SVN_fetch_log(SVN_Operator_Single_File, bpy.types.Operator):
    bl_idname = "svn.fetch_log"
    bl_label = "Fetch SVN Log"
    bl_description = "Update the SVN Log file with new log entries grabbed from the remote repository"
    bl_options = {'INTERNAL'}

    missing_file_allowed = True
    MAX_REVS_TO_DOWNLOAD = 10  # Number of revisions to download before writing to the file and the console. Bigger number means fewer "checkpoints" in case the process gets cancelled.

    def invoke(self, context, _event):
        """We want to use a modal operator to wait for the SVN process in the 
        background to finish. And once it's finished, we want to move on to 
        execute()."""

        svn = self.get_svn_data(context)
        if svn.log_update_in_progress:
            self.report({'ERROR'}, "An SVN Log process is already running!")
            return {'CANCELLED'}

        prefs = get_addon_prefs(context)
        current_rev = prefs.revision_number
        latest_log_rev = 0
        if len(svn.log) > 0:
            latest_log_rev = svn.log[-1].revision_number

        if latest_log_rev >= current_rev:
            self.report({'INFO'}, "Log is already up to date, cancelling.")
            return {'CANCELLED'}

        self.popen = None
        self.report({'INFO'}, "Begin updating SVN log, this may take a while. Autosave is now disabled! Click the button again to cancel.")
        svn.log_update_in_progress = True
        svn.log_update_cancel_flag = False
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, _event):
        prefs = get_addon_prefs(context)
        current_rev = prefs.revision_number
        svn = self.get_svn_data(context)

        if svn.log_update_cancel_flag:
            self.report({'INFO'}, "Log update cancelled.")
            svn.log_update_cancel_flag = False
            svn.log_update_in_progress = False
            return {'FINISHED'}

        latest_log_rev = 0
        if len(svn.log) > 0:
            latest_log_rev = svn.log[-1].revision_number

        if self.popen is None:
            # Start a sub-process.
            num_logs_to_get = current_rev - latest_log_rev
            if num_logs_to_get > self.MAX_REVS_TO_DOWNLOAD:
                # Do some clamping here while testing. TODO: remove once this successfully runs in the background!
                num_logs_to_get = self.MAX_REVS_TO_DOWNLOAD

            goal_rev = latest_log_rev + num_logs_to_get
            self.popen = self.execute_svn_command_nofreeze(context, f"svn log --verbose -r {latest_log_rev+1}:{goal_rev}")[0]

        if self.popen.poll() is None:
            # Sub-process is not finished yet, do nothing.
            return {'PASS_THROUGH'}

        # Sub-process has finished running, process it and start another.
        stdout_data, _stderr_data = self.popen.communicate()
        self.popen = None

        # Create the log file if it doesn't already exist.
        self.file_rel_path = ".svn/svn.log"
        filepath = self.get_file_full_path(context)

        file_existed = False
        if filepath.exists():
            file_existed = True
            read_svn_log_file(context, filepath)

        if latest_log_rev >= current_rev:
            self.report({'INFO'}, "Finished updating the SVN log!")
            svn.log_update_in_progress = False
            return {'FINISHED'}

        new_log = stdout_data.decode()
        with open(filepath, 'a+') as f:
            # Append to the file, create it if necessary.
            if file_existed:
                # We want to skip the first line of the svn log when continuing,
                # to avoid duplicate dashed lines, which would also mess up our
                # parsing logic.
                new_log = new_log[73:] # 72 dashes and a newline

            f.write(new_log)

        read_svn_log_file(context, filepath)

        self.report({'INFO'}, f"SVN Log now at r{context.scene.svn.log[-1].revision_number}")

        return {'RUNNING_MODAL'}


class SVN_fetch_log_cancel(bpy.types.Operator):
    bl_idname = "svn.fetch_log_cancel"
    bl_label = "Cancel Fetching SVN Log"
    bl_description = "Cancel the background process of fetching the SVN log"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        context.scene.svn.log_update_cancel_flag = True
        return {'FINISHED'}


class VIEW3D_PT_svn_log_files(bpy.types.Panel):
    """Display the files that were affected by the selected revision."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SVN'
    bl_label = 'Affected Files'
    bl_parent_id = "VIEW3D_PT_svn_log"
    bl_options = {'DEFAULT_CLOSED'}

    # TODO!


class SVN_show_commit_message(bpy.types.Operator):
    bl_idname = "svn.display_commit_message"
    bl_label = "" # Don't want the first line of the tooltip on mouse hover.
    bl_description = "Show the currently active commit, using a dynamic tooltip"
    bl_options = {'INTERNAL'}

    popup_width = 600

    log_rev: IntProperty(
        description = "Revision number of the log entry to show in the tooltip"
    )

    @classmethod
    def description(cls, context, properties):
        log_entry = context.scene.svn.get_log_by_revision(properties.log_rev)[1]
        return log_entry.commit_message

    def execute(self, context):
        context.scene.svn.log_active_index = context.scene.svn.get_log_by_revision(self.log_rev)[0]
        return {'FINISHED'}

registry = [SVN_file, SVN_log, VIEW3D_PT_svn_log, SVN_UL_log, SVN_fetch_log, SVN_fetch_log_cancel, SVN_show_commit_message]
