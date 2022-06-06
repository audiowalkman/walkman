import pyo


def camel_case_to_snake_case(camel_case_string: str) -> str:
    """Transform camel case formatted string to snake case.

    :param camel_case_string: String which is formatted using
        camel case (no whitespace, but upper letters at
        new word start).
    :return: string formatted using snake case

    **Example:** MyClassName -> my_class_name
    """

    character_list = []

    is_first = True
    for character in camel_case_string:
        if character.isupper():
            character = character.lower()
            if not is_first:
                character = "_{}".format(character)

        if is_first:
            is_first = False

        character_list.append(character)

    return "".join(character_list)


def decibel_to_amplitude_ratio(decibel: float, reference_amplitude: float = 1) -> float:
    """Convert decibel to amplitude ratio.

    :param decibel: The decibel number that shall be converted.
    :param reference_amplitude: The amplitude for decibel == 0.

    """
    return float(reference_amplitude * (10 ** (decibel / 20)))


def get_next_mixer_index(mixer: pyo.Mixer) -> int:
    try:
        index = max(mixer.getKeys()) + 1
    except ValueError:
        index = 0
    return index
