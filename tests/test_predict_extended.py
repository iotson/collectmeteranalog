import math
from unittest import mock

import numpy as np
import pytest
from PIL import Image

import collectmeteranalog.predict as predict_mod


class TestLoadInterpreter:
    def test_no_tflite_runtime(self):
        """If tensorflow is not available, should set has_tflite_runtime=False."""
        # Reset module state
        predict_mod.interpreter = None
        predict_mod.has_tflite_runtime = False
        predict_mod.model_path = None

        # Mock import failure
        with mock.patch.dict("sys.modules", {"tflite_runtime.interpreter": None}):
            with mock.patch.dict("sys.modules", {"tensorflow.lite": None}):
                result = predict_mod.load_interpreter("some_model.tflite")

        img = Image.new("RGB", (64, 64))
        assert predict_mod.predict(img) == -1

    def test_interpreter_allocation_error(self):
        """If interpreter fails to allocate, prediction stays disabled."""
        predict_mod.interpreter = None
        predict_mod.has_tflite_runtime = False
        predict_mod.model_path = None

        mock_tflite = mock.MagicMock()
        mock_tflite.Interpreter.side_effect = Exception("bad model")

        with mock.patch.dict("sys.modules", {
            "tflite_runtime": mock.MagicMock(),
            "tflite_runtime.interpreter": mock_tflite
        }):
            predict_mod.load_interpreter("bad_model.tflite")

        img = Image.new("RGB", (64, 64))
        assert predict_mod.predict(img) == -1


class TestPredictWithModel:
    def _setup_mock_interpreter(self, output_data):
        """Helper to set up a mock interpreter."""
        interp = mock.MagicMock()
        interp.get_input_details.return_value = [
            {"index": 0, "shape": np.array([1, 32, 32, 3])}
        ]
        interp.get_output_details.return_value = [{"index": 0}]
        interp.get_tensor.return_value = output_data

        predict_mod.interpreter = interp
        predict_mod.has_tflite_runtime = True
        predict_mod.model_path = "model.tflite"
        return interp

    def test_predict_ana_cont(self):
        """Test prediction with ana-cont model (2 outputs: sin, cos)."""
        # sin(2*pi*5/10)=0, cos(2*pi*5/10)=-1 => value=5.0
        output = np.array([[0.0, -1.0]], dtype=np.float32)
        self._setup_mock_interpreter(output)

        img = Image.new("RGB", (64, 64))
        result = predict_mod.predict(img)
        assert result == 5.0

    def test_predict_ana_class100(self):
        """Test prediction with ana-class100 model (100 outputs)."""
        output = np.zeros((1, 100), dtype=np.float32)
        output[0][35] = 1.0  # class 35 => value 3.5
        self._setup_mock_interpreter(output)

        img = Image.new("RGB", (64, 64))
        result = predict_mod.predict(img)
        assert result == 3.5

    def test_predict_unsupported_model(self):
        """Test prediction with unsupported number of outputs."""
        output = np.zeros((1, 50), dtype=np.float32)
        self._setup_mock_interpreter(output)

        img = Image.new("RGB", (64, 64))
        result = predict_mod.predict(img)
        assert result == -1

    def teardown_method(self):
        """Reset predict module state."""
        predict_mod.interpreter = None
        predict_mod.has_tflite_runtime = False
        predict_mod.model_path = None
