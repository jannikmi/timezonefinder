import itertools
from pathlib import Path
from typing import List, Optional

import h3.api.numpy_int as h3
import pydantic

import timezonefinder.configs
from timezonefinder import hex_helpers

PATH2CATS = Path(__file__).parent.parent / "data" / "task_categorisation"

# at least one category with this name must exist to have a valid selection in every hierarchy level
PLACEHOLDER_CAT = "other"


class TaskCategory(ImmutableBaseModel):
    """
    Model for representing the recursive tree structure of task categories
    """

    name: str
    sub_categories: Optional[List["TaskCategory"]]

    @pydantic.validator("name")
    def cat_name_is_valid(cls, v: str):
        if len(v) == 0:
            # TODO empty string?
            return v
        v_alpha = v.replace("_", "")
        assert v_alpha.isalnum(), (
            f'invalid category name: "{v}"'
            'category names must only contain alphanumeric characters or "_"'
        )
        assert v.islower(), "a category name must be lower cased"
        return v

    _validate_subcats = pydantic.validator("sub_categories", allow_reuse=True)(
        sub_categories_are_valid
    )
    _validate_root = pydantic.root_validator(allow_reuse=True)(placeholder_cat_is_leaf)

    def category_paths(self) -> List[str]:
        sub_cats = self.sub_categories
        paths = [self.name]
        if sub_cats is None:
            return paths

        sub_paths = list(
            itertools.chain.from_iterable(c.category_paths() for c in sub_cats)
        )
        paths += list(map(lambda sub_path: f"{self.name}.{sub_path}", sub_paths))
        return paths


class ImmutableBaseModel(pydantic.BaseModel):
    class Config:
        allow_mutation = False


shortcuts = hex_helpers.mapping


def test_resolutions():
    shortcut_hex_ids = shortcuts.keys()
    resolutions = map(lambda h: h3.h3_get_resolution(h), shortcut_hex_ids)
    min_resolution = min(resolutions)
    assert (
        timezonefinder.configs.MIN_RES == min_resolution
    ), f"minimum found resolution {min_resolution} does not match the setting {timezonefinder.configs.MIN_RES}"

    max_resolution = max(resolutions)
    assert (
        timezonefinder.configs.MAX_RES == max_resolution
    ), f"minimum found resolution {max_resolution} does not match the setting {timezonefinder.configs.MAX_RES}"
