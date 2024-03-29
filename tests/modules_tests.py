import typing
import unittest

import pyo

import walkman


class ModuleContainerTest(walkman.unit_tests.WalkmanTestCase, unittest.TestCase):
    def test_get_module_name_to_module_class_dict(self):
        module_name_to_module_class_dict = {}
        for module_name in walkman.modules.buildins.__all__:
            module_class = getattr(walkman, module_name)
            module_name_to_module_class_dict.update(
                {module_class.get_class_name(): module_class}
            )
        self.assertEqual(
            walkman.ModuleContainer.get_module_name_to_module_class_dict(),
            module_name_to_module_class_dict,
        )

    def test_from_module_configuration(self):
        module_name_to_replication_configuration_dict = {
            "sine": {"modern": {"default_dict": {"frequency": {"value": 440}}}}
        }
        module_container = walkman.ModuleContainer.from_module_configuration(
            module_name_to_replication_configuration_dict
        )
        self.assertEqual(len(module_container), 3)
        self.assertTrue("sine" in module_container)
        self.assertTrue("value" in module_container)
        self.assertTrue("modern" in module_container["sine"])
        self.assertEqual(
            module_container["sine"]["modern"].default_dict,
            {"frequency": {"value": 440}},
        )


class ModuleTest(walkman.unit_tests.ModuleWithFaderTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()

        class SineModule(walkman.ModuleWithFader):
            def __init__(self, mul: float = 0.5, **kwargs):
                self.mul = mul
                super().__init__(**kwargs)

            def setup_pyo_object(self):
                super().setup_pyo_object()
                self.sine = pyo.Sine(mul=self.mul).stop()
                self.internal_pyo_object_list.append(self.sine)

            @property
            def _pyo_object(self) -> pyo.PyoObject:
                return self.sine

            def _initialise(self, frequency: float = 1000):
                self.sine.setFreq(frequency)

        class FilterModule(
            walkman.ModuleWithFader,
            audio_input=walkman.AutoSetup(SineModule),
            dummy_input=walkman.AutoSetup(SineModule, implicit=False),
        ):
            def setup_pyo_object(self):
                super().setup_pyo_object()
                self.biquad = pyo.Biquad(input=self.audio_input.pyo_object).stop()
                self.internal_pyo_object_list.append(self.biquad)

            @property
            def _pyo_object(self) -> pyo.PyoObject:
                return self.biquad

        class NestedFilterModule(
            FilterModule, audio_input=walkman.AutoSetup(FilterModule)
        ):
            ...

        self.SineModule = SineModule
        self.FilterModule = FilterModule
        self.NestedFilterModule = NestedFilterModule

    def get_module_class(self) -> typing.Type[walkman.Module]:
        return self.SineModule

    def get_filter_module_instance(self, **kwargs):
        return self.get_module_instance(**kwargs, module_class=self.FilterModule)

    def test_hash(self):
        self.assertTrue(hash(self.get_module_instance()))

    def test_deep_inheritance(self):
        self.assertNotEqual(
            self.FilterModule.default_module_input_dict,
            self.NestedFilterModule.default_module_input_dict,
        )

    def test_init_simple(self):
        module_instance = self.SineModule()
        self.assertTrue(bool(module_instance))

    def test_init_with_argument(self):
        module_instance = self.SineModule(mul=0.32)
        module_instance.setup_pyo_object()
        self.assertEqual(module_instance.mul, 0.32)
        self.assertEqual(module_instance.mul, module_instance.sine.mul)

    def test_init_module_with_module_inputs(self):
        module_instance = self.FilterModule()
        self.assertTrue("audio_input" in module_instance.module_input_dict)
        self.assertTrue(
            isinstance(
                module_instance.module_input_dict["audio_input"], walkman.ModuleInput
            )
        )
        self.assertEqual(
            type(module_instance.module_input_dict["audio_input"]), walkman.AutoSetup
        )

    def test_assign_module_inputs(self):
        module_instance = self.FilterModule()
        self.assertFalse(hasattr(module_instance, "audio_input"))

        module_container = walkman.ModuleContainer({})
        module_instance.assign_module_inputs(module_container)

        self.assertTrue(hasattr(module_instance, "audio_input"))
        self.assertTrue(isinstance(module_instance.audio_input, walkman.Module))
        self.assertTrue("sine_module" in module_container)
        self.assertEqual(2, len(module_container["sine_module"]))

    def test_setup_pyo_object(self):
        module_instance = self.SineModule()
        self.assertFalse(hasattr(module_instance, "fader"))

        module_instance.setup(walkman.ModuleContainer({}))
        self.assertTrue(hasattr(module_instance, "fader"))

    def test_setup(self):
        module_instance = self.SineModule()
        self.assertFalse(hasattr(module_instance, "sine"))

        module_instance.setup(walkman.ModuleContainer({}))
        self.assertTrue(hasattr(module_instance, "sine"))

    def initialise_with_argument(self):
        module_instance = self.SineModule()
        frequency = 13.4124
        self.assertNotEqual(module_instance.sine.getFreq(), frequency)

        module_instance.initialise(frequency=frequency)
        self.assertEqual(module_instance.sine.getFreq(), frequency)

    def test_default_dict(self):
        frequency = 31313
        module_instance = self.get_module_instance(
            default_dict={"frequency": frequency}
        )
        module_instance.initialise()
        self.assertEqual(module_instance.sine.freq, frequency)

    def test_module_input_chain_simple(self):
        module_instance = self.get_module_instance(module_class=self.FilterModule)

        self.assertEqual(
            module_instance.module_input_chain,
            (
                module_instance.dummy_input.base,
                module_instance.audio_input.base,
            ),
        )

    def test_module_input_chain_two_levels(self):
        module_instance = self.get_module_instance(module_class=self.NestedFilterModule)

        self.assertEqual(len(module_instance.module_input_chain), 4)
        self.assertEqual(
            module_instance.module_input_chain,
            (
                module_instance.dummy_input.base,
                module_instance.audio_input.dummy_input.base,
                module_instance.audio_input.audio_input.base,
                module_instance.audio_input.base,
            ),
        )

    def test_implicit_module_input_chain(self):
        module_instance = self.get_module_instance(module_class=self.NestedFilterModule)
        self.assertEqual(
            module_instance.implicit_module_input_chain,
            (
                module_instance.audio_input.audio_input.base,
                module_instance.audio_input.base,
            ),
        )

    def test_module_output_chain(self):
        module_instance = self.get_module_instance(module_class=self.NestedFilterModule)
        module_output_chain = (
            module_instance.audio_input.audio_input.module_output_chain
        )
        self.assertEqual(len(module_output_chain), 2)
        self.assertEqual(
            module_output_chain,
            (module_instance.audio_input.base, module_instance.base),
        )

    def test_module_chain(self):
        module_instance = self.get_module_instance(module_class=self.NestedFilterModule)
        self.assertEqual(
            module_instance.audio_input.module_chain,
            (
                module_instance.audio_input.dummy_input.base,
                module_instance.audio_input.audio_input.base,
                module_instance.base,
            ),
        )

    def test_implicit_module_chain(self):
        module_instance = self.get_module_instance(module_class=self.NestedFilterModule)
        self.assertEqual(
            module_instance.audio_input.implicit_module_chain,
            (
                module_instance.audio_input.audio_input.base,
                module_instance.base,
            ),
        )

    def test_initialise_syntactic_sugar_0(self):
        module_instance = self.get_module_instance(module_class=self.FilterModule)
        frequency = 33.33
        self.assertNotEqual(module_instance.audio_input.sine.freq, frequency)

        module_instance.initialise(audio_input={"frequency": frequency})
        self.assertEqual(module_instance.audio_input.sine.freq, frequency)


class ParameterTest(walkman.unit_tests.ModuleTestCase, unittest.TestCase):
    def get_module_class(self) -> typing.Type[walkman.Module]:
        return walkman.Parameter

    def get_module_instance(
        self,
        module_class: typing.Optional[typing.Type[walkman.Module]] = None,
        **kwargs
    ) -> walkman.Module:
        return super().get_module_instance(
            default_dict={"value": [[0, 0], [20, 1]]},
            module_class=module_class,
            **kwargs
        )

    def test_float_value(self):
        module_instance = self.get_module_instance()
        value = 200
        # XXX: Portamento takes longer than it says.
        # To avoid test failure we add a rounding time.
        portamento_duration_tolerance = 0.01
        module_instance.initialise(value=value)
        module_instance.play()
        self.jump_to(
            module_instance.fade_in_duration
            + module_instance.portamento.risetime
            + portamento_duration_tolerance
        )
        # XXX: Because of Portamento the value is not exactly
        # reached. To Avoid test failure we accept a certain
        # tolerance.
        self.assertAlmostEqual(module_instance.pyo_object.get(), value, places=1)


# TODO(mock audio input!)
# class AudioInputTest(walkman.unit_tests.ModuleTestCase):
#     def get_module_class(self) -> typing.Type[walkman.Module]:
#         return walkman.AudioInput

# TODO(mock midi input!)
# class MidiControlInputTest(walkman.unit_tests.ModuleTestCase):
#     def get_module_class(self) -> typing.Type[walkman.Module]:
#         return walkman.MidiControlInput


class SineTest(walkman.unit_tests.ModuleTestCase, unittest.TestCase):
    def get_module_class(self) -> typing.Type[walkman.Module]:
        return walkman.Sine


class AmplificationTest(walkman.unit_tests.ModuleTestCase, unittest.TestCase):
    def get_module_class(self) -> typing.Type[walkman.Module]:
        class AmplificationForTest(
            walkman.Amplification,
            audio_input=walkman.AutoSetup(walkman.Sine),
        ):
            pass

        return AmplificationForTest


class MixerTest(walkman.unit_tests.ModuleTestCase, unittest.TestCase):
    def get_module_class(self) -> typing.Type[walkman.Module]:
        class MixerForTest(
            walkman.Mixer, audio_input_0=walkman.AutoSetup(walkman.Sine)
        ):
            pass

        return MixerForTest


class FilterTest(walkman.unit_tests.ModuleTestCase, unittest.TestCase):
    def get_module_class(self) -> typing.Type[walkman.Module]:
        class FilterForTest(
            walkman.Filter,
            audio_input=walkman.AutoSetup(walkman.Sine),
        ):
            pass

        return FilterForTest


class ConvolutionReverbTest(walkman.unit_tests.ModuleTestCase, unittest.TestCase):
    def get_module_class(self) -> typing.Type[walkman.Module]:
        class ConvolutionReverbForTest(
            walkman.ConvolutionReverb,
            audio_input=walkman.AutoSetup(walkman.Sine),
        ):
            pass

        return ConvolutionReverbForTest

    def get_module_instance(
        self,
        module_class: typing.Optional[typing.Type[walkman.Module]] = None,
        **kwargs
    ) -> walkman.Module:
        return super().get_module_instance(
            module_class=module_class, impulse_path="tests/impulse.wav", **kwargs
        )


class WaveguideReverbTest(walkman.unit_tests.ModuleTestCase, unittest.TestCase):
    def get_module_class(self) -> typing.Type[walkman.Module]:
        class WaveguideReverbForTest(
            walkman.WaveguideReverb,
            audio_input=walkman.AutoSetup(walkman.Sine),
        ):
            pass

        return WaveguideReverbForTest


class ButterworthHighpassFilterTest(
    walkman.unit_tests.ModuleTestCase, unittest.TestCase
):
    def get_module_class(self) -> typing.Type[walkman.Module]:
        class ButterworthHighpassFilterForTest(
            walkman.ButterworthHighpassFilter,
            audio_input=walkman.AutoSetup(walkman.Sine),
        ):
            pass

        return ButterworthHighpassFilterForTest


class ButterworthLowpassFilterTest(
    walkman.unit_tests.ModuleTestCase, unittest.TestCase
):
    def get_module_class(self) -> typing.Type[walkman.Module]:
        class ButterworthLowpassFilterForTest(
            walkman.ButterworthLowpassFilter,
            audio_input=walkman.AutoSetup(walkman.Sine),
        ):
            pass

        return ButterworthLowpassFilterForTest


class EqualizerTest(walkman.unit_tests.ModuleTestCase, unittest.TestCase):
    def get_module_class(self) -> typing.Type[walkman.Module]:
        class EqualizerForTest(
            walkman.Equalizer,
            audio_input=walkman.AutoSetup(walkman.Sine),
        ):
            pass

        return EqualizerForTest


class AverageTest(walkman.unit_tests.ModuleTestCase, unittest.TestCase):
    def get_module_class(self) -> typing.Type[walkman.Module]:
        class AverageForTest(
            walkman.Average,
            audio_input=walkman.AutoSetup(walkman.Sine),
        ):
            pass

        return AverageForTest


class IRAverageTest(walkman.unit_tests.ModuleTestCase, unittest.TestCase):
    def get_module_class(self) -> typing.Type[walkman.Module]:
        class IRAverageForTest(
            walkman.IRAverage,
            audio_input=walkman.AutoSetup(walkman.Sine),
        ):
            pass

        return IRAverageForTest


class HubTest(walkman.unit_tests.WalkmanTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        module_name_to_replication_configuration_dict = {
            "sine": {"0": {}, "1": {}, "2": {}},
            "hub": {
                "0": {
                    "audio_input_0": "sine.0",
                    "audio_input_1": "sine.1",
                    "audio_input_2": "sine.2",
                    "audio_input_index_to_pyo_object_index": {0: 0, 2: 1},
                }
            },
            "amplification": {
                "0": {"audio_input": "hub.0.0", "send_to_physical_output": True},
                "1": {"audio_input": "hub.0.1", "send_to_physical_output": True},
            },
        }
        self.module_container = walkman.ModuleContainer.from_module_configuration(
            module_name_to_replication_configuration_dict
        )

    def test_sine_0_is_audible(self):
        self.assertSineIsAudible("0", "0")

    def test_sine_2_is_audible(self):
        self.assertSineIsAudible("2", "1")

    def assertSineIsAudible(self, sine_index: str, amplification_index: str):
        s = self.module_container["sine"][sine_index]
        h = self.module_container["hub"]["0"]
        a = self.module_container["amplification"][amplification_index]
        self.assertIsSilent(s.pyo_object)
        self.assertIsSilent(a.pyo_object)
        s.play()
        self.assertIsNotSilent(s.pyo_object)
        h.play()
        a.play()
        self.assertIsNotSilent(a.pyo_object)
        s.stop()
        h.stop()
        a.stop()

