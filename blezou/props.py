import bpy
from bpy.app.handlers import persistent
from .types import ZProject, ZSequence, ZShot, ZAssetType, ZAsset
from dataclasses import asdict
from .logger import ZLoggerFactory
from typing import Optional, Any

logger = ZLoggerFactory.getLogger(name=__name__)

_ZSEQUENCE_ACTIVE: ZSequence = ZSequence()
_ZSHOT_ACTIVE: ZShot = ZShot()
_ZASSET_ACTIVE: ZAsset = ZAsset()
_ZASSET_TYPE_ACTIVE: ZAssetType = ZAssetType()


class BZ_PopertyGroup_SEQ_Shot(bpy.types.PropertyGroup):
    """
    Property group that will be registered on sequence strips.
    They hold metadata that will be used to compose a data structure that can
    be pushed to backend.
    """

    # shot
    shot_id: bpy.props.StringProperty(name="Shot ID")  # type: ignore
    shot_name: bpy.props.StringProperty(name="Shot", default="")  # type: ignore
    shot_description: bpy.props.StringProperty(name="Description", default="")  # type: ignore

    # sequence
    sequence_name: bpy.props.StringProperty(name="Seq", default="")  # type: ignore
    sequence_id: bpy.props.StringProperty(name="Seq ID", default="")  # type: ignore

    # project
    project_name: bpy.props.StringProperty(name="Project", default="")  # type: ignore
    project_id: bpy.props.StringProperty(name="Project ID", default="")  # type: ignore

    # meta
    initialized: bpy.props.BoolProperty(  # type: ignore
        name="Initialized", default=False, description="Is Blezou shot"
    )
    linked: bpy.props.BoolProperty(  # type: ignore
        name="Linked", default=False, description="Is linked to an ID in gazou"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.shot,
            "sequence_name": self.sequence,
            "description": self.description,
        }

    def clear(self):
        self.shot_id = ""
        self.shot_name = ""
        self.shot_description = ""

        self.sequence_id = ""
        self.sequence_name = ""

        self.project_name = ""
        self.project_id = ""

        self.initialized = False
        self.linked = False


class BZ_PopertyGroup_BlezouData(bpy.types.PropertyGroup):
    """"""

    sequence_active_id: bpy.props.StringProperty(  # type: ignore
        name="active sequence id",
        description="Gazou Id that refers to the active sequence",
        default="",
        options={"HIDDEN", "SKIP_SAVE"},
    )
    shot_active_id: bpy.props.StringProperty(  # type: ignore
        name="active shot id",
        description="Gazou Id that refers to the active project",
        default="",
        options={"HIDDEN", "SKIP_SAVE"},
    )
    asset_active_id: bpy.props.StringProperty(  # type: ignore
        name="active asset id",
        description="Gazou Id that refers to the active asset",
        default="",
        options={"HIDDEN", "SKIP_SAVE"},
    )
    asset_type_active_id: bpy.props.StringProperty(  # type: ignore
        name="active asset_type id",
        description="Gazou Id that refers to the active asset_type",
        default="",
        options={"HIDDEN", "SKIP_SAVE"},
    )

    def clear(self):
        self.sequence_active_id = ""
        self.shot_active_id = ""
        self.asset_active_id = ""
        self.asset_type_active_id = ""


def init_cache_variables(context: bpy.types.Context = bpy.context) -> None:
    global _ZSEQUENCE_ACTIVE
    global _ZSHOT_ACTIVE
    global _ZASSET_ACTIVE
    global _ZASSET_TYPE_ACTIVE

    sequence_active_id = context.scene.blezou.sequence_active_id
    shot_active_id = context.scene.blezou.shot_active_id
    asset_active_id = context.scene.blezou.asset_active_id
    asset_type_active_id = context.scene.blezou.asset_type_active_id

    if sequence_active_id:
        _ZSEQUENCE_ACTIVE = ZSequence.by_id(sequence_active_id)
        logger.info(f"Initialized Active Sequence Cache to: {_ZSEQUENCE_ACTIVE.name}")

    if shot_active_id:
        _ZSHOT_ACTIVE = ZShot.by_id(shot_active_id)
        logger.info(f"Initialized Active Shot Cache to: {_ZSHOT_ACTIVE.name}")

    if asset_active_id:
        _ZASSET_ACTIVE = ZAsset.by_id(asset_active_id)
        logger.info(f"Initialized Active Asset Cache to: {_ZASSET_ACTIVE.name}")

    if asset_type_active_id:
        _ZASSET_TYPE_ACTIVE = ZAssetType.by_id(asset_type_active_id)
        logger.info(
            f"Initialized Active Asset Type Cache to: {_ZASSET_TYPE_ACTIVE.name}"
        )


def clear_cache_variables():
    global _ZSEQUENCE_ACTIVE
    global _ZSHOT_ACTIVE
    global _ZASSET_ACTIVE
    global _ZASSET_TYPE_ACTIVE

    _ZSEQUENCE_ACTIVE = ZSequence()
    logger.info("Cleared Active Sequence Cache")
    _ZSHOT_ACTIVE = ZShot()
    logger.info("Cleared Active Shot Cache")
    _ZASSET_ACTIVE = ZAsset()
    logger.info("Cleared Active Asset Cache")
    _ZASSET_TYPE_ACTIVE = ZAssetType()
    logger.info("Cleared Active Asset Type Cache")


@persistent
def load_post_handler(dummy):
    clear_cache_variables()


# ----------------REGISTER--------------

classes = [BZ_PopertyGroup_SEQ_Shot, BZ_PopertyGroup_BlezouData]


def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Sequence.blezou = bpy.props.PointerProperty(
        name="Blezou",
        type=BZ_PopertyGroup_SEQ_Shot,
        description="Metadata that is required for blezou",
    )
    bpy.types.Scene.blezou = bpy.props.PointerProperty(
        name="Blezou",
        type=BZ_PopertyGroup_BlezouData,
        description="Metadata that is required for blezou",
    )

    bpy.app.handlers.load_post.append(load_post_handler)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # clear cache
    clear_cache_variables()
