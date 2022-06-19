import typing

import pyo


__all__ = ("ChannelMapping", "dict_or_channel_mapping_to_channel_mapping")


class ChannelMapping(typing.Dict[int, typing.Tuple[int, ...]]):
    """Map audio channels to other audio channels.

    Left side is always one channel, right side can be one
    or more channels.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Hack to ensure key/values are integer
        key_to_remove_list = []
        update_dict = {}
        for key, value in self.items():
            if not isinstance(key, int):
                key_to_remove_list.append(key)
            if isinstance(value, (str, int)):
                output_channel_list = [value]
            else:
                output_channel_list = value
            output_channel_tuple = tuple(
                int(output_channel) for output_channel in output_channel_list
            )
            update_dict[int(key)] = output_channel_tuple
        self.update(update_dict)
        for key in key_to_remove_list:
            del self[key]

    @property
    def left_channel_set(self) -> typing.Set[int]:
        return set(self.keys())

    @property
    def maxima_left_channel(self) -> int:
        return max(self.left_channel_set) + 1

    @property
    def right_channel_tuple_tuple(self) -> typing.Tuple[typing.Tuple[int, ...], ...]:
        return tuple(self.values())

    @property
    def right_channel_set(self) -> typing.Set[int]:
        right_channel_set = set([])
        for right_channel_tuple in self.right_channel_tuple_tuple:
            for right_channel in right_channel_tuple:
                right_channel_set.add(right_channel)
        return right_channel_set

    @property
    def maxima_right_channel(self) -> int:
        return max(self.right_channel_set) + 1

    def to_mixer(self) -> pyo.Mixer:
        return pyo.Mixer(outs=self.maxima_right_channel)


def dict_or_channel_mapping_to_channel_mapping(
    dict_or_channel_mapping_to_channel_mapping: typing.Union[dict, ChannelMapping]
) -> ChannelMapping:
    if not isinstance(dict_or_channel_mapping_to_channel_mapping, ChannelMapping):
        channel_mapping = ChannelMapping(dict_or_channel_mapping_to_channel_mapping)
    else:
        channel_mapping = dict_or_channel_mapping_to_channel_mapping
    return channel_mapping
