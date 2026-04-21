from PIL import Image

from collectmeteranalog.predict import predict, load_interpreter


class TestPredict:
    def test_predict_disabled_by_default(self):
        """predict() returns -1 when no model is loaded."""
        img = Image.new("RGB", (64, 64), color="red")
        assert predict(img) == -1

    def test_load_interpreter_off(self):
        """load_interpreter with 'off' returns -1."""
        result = load_interpreter("off")
        assert result == -1

    def test_load_interpreter_none(self):
        """load_interpreter with None returns -1."""
        result = load_interpreter(None)
        assert result == -1

    def test_load_interpreter_nonexistent_model(self):
        """load_interpreter with invalid path doesn't crash."""
        load_interpreter("/nonexistent/model.tflite")
        img = Image.new("RGB", (64, 64), color="blue")
        assert predict(img) == -1
