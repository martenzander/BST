import bpy
from typing import List, Tuple, Optional

_SQE_NOT_LINKED: List[Tuple[str, str, str]] = []
_SQE_DUPLCIATES: List[Tuple[str, str, str]] = []


def _sqe_get_not_linked(self, context):
    return _SQE_NOT_LINKED


def _sqe_get_duplicates(self, context):
    return _SQE_DUPLCIATES


def _sqe_update_not_linked(context: bpy.types.Context) -> List[Tuple[str, str, str]]:
    """get all strips that are initialized but not linked yet"""
    enum_list = []

    if context.selected_sequences:
        strips = context.selected_sequences
    else:
        strips = context.scene.sequence_editor.sequences_all

    for strip in strips:
        if strip.blezou.initialized and not strip.blezou.linked:
            enum_list.append((strip.name, strip.name, ""))

    return enum_list


def _sqe_update_duplicates(context: bpy.types.Context) -> List[Tuple[str, str, str]]:
    """get all strips that are initialized but not linked yet"""
    enum_list = []
    data_dict = {}
    if context.selected_sequences:
        strips = context.selected_sequences
    else:
        strips = context.scene.sequence_editor.sequences_all

    # create data dict that holds all shots ids and the corresponding strips that are linked to it
    for i in range(len(strips)):

        if strips[i].blezou.linked:
            # get shot_id, shot_name, create entry in data_dict if id not existent
            shot_id = strips[i].blezou.id
            shot_name = strips[i].blezou.shot
            if shot_id not in data_dict:
                data_dict[shot_id] = {"name": shot_name, "strips": []}

            # append i to strips list
            if strips[i] not in set(data_dict[shot_id]["strips"]):
                data_dict[shot_id]["strips"].append(strips[i])

            # comparet to all other strip
            for j in range(i + 1, len(strips)):
                if shot_id == strips[j].blezou.id:
                    data_dict[shot_id]["strips"].append(strips[j])

    # convert in data strucutre for enum property
    for shot_id, data in data_dict.items():
        if len(data["strips"]) > 1:
            enum_list.append(("", data["name"], shot_id))
            for strip in data["strips"]:
                enum_list.append((strip.name, strip.name, ""))

    return enum_list