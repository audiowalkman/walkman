import walkman


class OutputProviderTest(walkman.unit_tests.WalkmanTestCase):
    def test_register_audio_object(self):
        output_provider = walkman.OutputProvider()
        sine_audio_object = walkman.unit_tests.SineAudioObject()
        self.assertEqual(output_provider.register_audio_object(sine_audio_object), (0,))
        self.assertEqual(output_provider.register_audio_object(sine_audio_object), (1,))

    def test_activate_channel_mapping_simple(self):
        sine_audio_object = walkman.unit_tests.SineAudioObject()
        sine_audio_object.pyo_object.play()

        self.assertTrue(self.is_pyo_object_not_silent(sine_audio_object.pyo_object))

        output_provider = walkman.OutputProvider()
        pyo_object_mixer_tuple = (
            walkman.PyoObjectMixer(output_provider.module_mixer[0]),
            walkman.PyoObjectMixer(output_provider.module_mixer[1]),
        )

        for pyo_object_mixer in pyo_object_mixer_tuple:
            self.assertFalse(self.is_pyo_object_not_silent(pyo_object_mixer))

        output_provider.activate_channel_mapping(
            sine_audio_object, walkman.ChannelMapping({0: 0})
        )

        self.assertTrue(sine_audio_object.name in output_provider.name_to_mixer_info)

        self.assertTrue(self.is_pyo_object_not_silent(pyo_object_mixer_tuple[0]))
        self.assertFalse(self.is_pyo_object_not_silent(pyo_object_mixer_tuple[1]))
