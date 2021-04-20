import json
import os

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Union, Optional, Tuple, Dict
from copy import deepcopy

import bpy

from . import prefs, props
from .logger import LoggerFactory

logger = LoggerFactory.getLogger(__name__)


_CACHECONFIG_TEMPL: Dict[str, Any] = {
    "meta": {"name": "", "creation_date": ""},
    "libs": {},  # {filepath_to_lib: _LIBDICT_TEMPL}
}

_LIBDICT_TEMPL: Dict[str, Any] = {
    "data_from": {"collections": {}},  # {'colname': {'cachefile': cachepath}}
}

_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def gen_filename_collection(collection: bpy.types.Collection) -> str:
    return f"{collection.name}.abc"


def gen_cachepath_collection(
    collection: bpy.types.Collection, context: bpy.types.Context
) -> Path:
    addon_prefs = prefs.addon_prefs_get(context)
    cachedir_path = Path(addon_prefs.cachedir_path)

    if not cachedir_path:
        raise ValueError(
            f"Failed to generate cachepath for collection: {collection.name}. Invalid cachepath: {str(cachedir_path)}"
        )
    return cachedir_path.joinpath(gen_filename_collection(collection)).absolute()


def get_current_time_string(date_format: str) -> str:
    now = datetime.now()
    current_time_string = now.strftime(date_format)
    return current_time_string


def read_json(filepath: Path) -> List[Dict[str, Any]]:
    with open(filepath.as_posix(), "r") as file:
        json_dict = json.loads(file.read())
        return json_dict


def save_as_json(data: Any, filepath: Path) -> None:
    with open(filepath.as_posix(), "w+") as file:
        json.dump(data, file, indent=4)


class CacheConfig:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self._json_obj: List[Dict[str, Any]] = []

        self.load(filepath)

    def load(self, filepath: Path) -> None:
        self.filepath = filepath
        self._json_obj = read_json(self.filepath)
        logger.info("Loaded cacheconfig from: %s", filepath.as_posix())

    @property
    def json_obj(self) -> List[Dict[str, Any]]:
        return self._json_obj

    def process(self, context: bpy.types.Context) -> None:
        logger.info("-START- Processing cacheconfig: %s", self.filepath.as_posix())
        if not self._is_filepath():
            raise RuntimeError("Failed to process CacheConfig. Filepath is not valid")

        colls = self._process_json_obj(context)
        logger.info("-END- Processing cacheconfig: %s", self.filepath.as_posix())

    def _process_json_obj(
        self, context: bpy.types.Context
    ) -> List[bpy.types.Collection]:

        # list of collections to track which ones got imported
        colls: List[bpy.types.Collection] = []

        for libfile in self._json_obj["libs"]:

            libpath = Path(libfile)
            colldata = self._json_obj["libs"][libfile]["data_from"]["collections"]

            with bpy.data.libraries.load(libpath.as_posix(), relative=True) as (
                data_from,
                data_to,
            ):

                for coll_name in colldata:
                    cachefile = colldata[coll_name]["cachefile"]

                    if coll_name not in data_from.collections:
                        logger.warning(
                            "Failed to import collection %s from %s. Doesn't exist in file.",
                            coll_name,
                            libpath.as_posix(),
                        )
                        continue

                    if coll_name in data_to.collections:
                        logger.warning("Collection %s already in blendfile.", coll_name)
                        continue

                    data_to.collections.append(coll_name)
                    logger.info(
                        "Appended collection: %s from library: %s",
                        coll_name,
                        libpath.as_posix(),
                    )

            # link collections in current scene and add cm.cachfile property
            for coll_name in colldata:
                cachefile = colldata[coll_name]["cachefile"]

                coll = bpy.data.collections[coll_name]

                try:
                    bpy.context.scene.collection.children.link(coll)
                except RuntimeError:
                    logger.warning("Collection %s already in blendfile.", coll_name)

                # set cm.cachefile property
                coll.cm.cachefile = cachefile
                self._add_coll_to_cm_collections(context, coll)
                colls.append(coll)

        return colls

    def _add_coll_to_cm_collections(
        self, context: bpy.types.Context, coll: bpy.types.Collection
    ) -> bpy.types.Collection:
        scn = context.scene
        if coll.name in [c[1].name for c in scn.cm_collections.items()]:
            logger.info("%s already in the cache collections list", coll.name)

        else:
            item = scn.cm_collections.add()
            item.coll_ptr = coll
            item.name = item.coll_ptr.name
            scn.cm_collections_index = len(scn.cm_collections) - 1

            logger.info("%s added to cache collections list", item.name)

        return coll

    def _is_filepath(self) -> bool:
        if not self.filepath:
            logger.error("CacheConfig has no valid filepath. Not loaded yet?")
            return False

        if not self.filepath.exists():
            logger.error("CacheConfig filepath does not exists on disk.")
            return False

        return True

    """
    def save(self) -> None:
        if not self._is_filepath():
            raise RuntimeError("Failed to save CacheConfig. Filepath is not valid")

        if not self._json_obj:
            raise RuntimeError("Failed to save CacheConfig. No data to save.")

        save_as_json(self._json_obj, self.filepath)
    """


class CacheConfigFactory:
    @classmethod
    def gen_config_from_scene(
        cls, context: bpy.types.Context, filepath: Path
    ) -> CacheConfig:
        addon_prefs = prefs.addon_prefs_get(context)
        cachedir_path = Path(addon_prefs.cachedir_path)
        _json_obj: Dict[str, Any] = deepcopy(_CACHECONFIG_TEMPL)
        scn = context.scene

        # populate metadata
        _json_obj["meta"]["name"] = Path(bpy.data.filepath).name
        _json_obj["meta"]["creation_date"] = get_current_time_string(_DATE_FORMAT)

        for lib in bpy.data.libraries:
            lib_items = lib.users_id
            libfile = Path(os.path.abspath(bpy.path.abspath(lib.filepath))).as_posix()

            for item in lib_items:
                # skip if not collection
                if item.bl_rna.identifier != "Collection":
                    continue

                # skip if this collection is not in the cache collection list
                if bpy.data.collections[item.name] not in list(
                    props.get_cache_collections(bpy.context)
                ):
                    continue

                coll = item

                # gen libfile key in _json_obj["libs"] if not existent
                if libfile not in _json_obj["libs"]:
                    _json_obj["libs"][libfile] = deepcopy(_LIBDICT_TEMPL)

                # gen collk key in _json_obj["libs"][libfile]['data_from']["collections"] if not existent
                if (
                    coll.name
                    not in _json_obj["libs"][libfile]["data_from"]["collections"]
                ):
                    _json_obj["libs"][libfile]["data_from"]["collections"][
                        coll.name
                    ] = {}

                # create collection dict based on this collection
                _col_dict = {
                    "cachefile": gen_cachepath_collection(coll, bpy.context).as_posix(),
                }

                # append collection dict to libdict
                _json_obj["libs"][libfile]["data_from"]["collections"][
                    coll.name
                ] = _col_dict

        # save json obj to disk
        save_as_json(_json_obj, filepath)
        logger.info("Generated cacheconfig and saved to: %s", filepath.as_posix())

        return CacheConfig(filepath)

    @classmethod
    def load_config_from_file(cls, filepath: Path) -> CacheConfig:
        if not filepath.exists():
            raise ValueError(
                f"Failed to load config. Path does not exist: {filepath.as_posix()}"
            )

        return CacheConfig(filepath)
