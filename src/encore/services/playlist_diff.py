from dataclasses import dataclass


@dataclass(frozen=True)
class PlaylistDiff:
    to_add: list[str]
    to_remove: list[str]


def diff_track_lists(old: list[str], new: list[str]) -> PlaylistDiff:
    old_set = set(old)
    new_set = set(new)
    to_add = [t for t in new if t not in old_set]
    to_remove = [t for t in old if t not in new_set]
    return PlaylistDiff(to_add=to_add, to_remove=to_remove)
