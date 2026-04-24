import math

import numpy as np

# Module-level state (public for test-injection and backward compatibility)
has_tflite_runtime = False
model_path = None
interpreter = None

_MODEL_CLASSES_CONT = 2
_MODEL_CLASSES_CLASS100 = 100
_DISABLED = -1


def load_interpreter(path):
    """Load and initialise a TFLite model from *path*.

    Returns -1 when prediction is disabled (no path, 'off', or missing runtime).
    Returns None on success.
    """
    global has_tflite_runtime, interpreter, model_path

    model_path = path
    interpreter = None
    has_tflite_runtime = False

    if model_path is None or model_path == "off":
        print("Prediction by model disabled: No model selected")
        return _DISABLED

    tflite = _import_tflite()
    if tflite is None:
        return _DISABLED

    if not _init_interpreter(tflite):
        return _DISABLED

    _detect_model_type()
    return None


def predict(image):
    """Run inference on *image* and return the predicted dial value.

    Returns -1 when prediction is disabled or the model type is unknown.
    """
    if model_path is None or model_path == "off" or not has_tflite_runtime or interpreter is None:
        return _DISABLED

    input_details = interpreter.get_input_details()
    input_index = input_details[0]["index"]
    input_shape = input_details[0]["shape"]
    output_index = interpreter.get_output_details()[0]["index"]

    resized = image.resize((input_shape[2], input_shape[1]))
    tensor = np.expand_dims(np.array(resized).astype(np.float32), axis=0)
    interpreter.set_tensor(input_index, tensor)
    interpreter.invoke()
    output = interpreter.get_tensor(output_index)

    num_classes = len(output[0])
    if num_classes == _MODEL_CLASSES_CONT:
        out_sin, out_cos = output[0][0], output[0][1]
        return round(((np.arctan2(out_sin, out_cos) / (2 * math.pi)) % 1) * 10, 1)
    if num_classes == _MODEL_CLASSES_CLASS100:
        return float((np.argmax(output, axis=1).reshape(-1) / 10)[0])

    print(f"Model type not supported. Detected classes: {num_classes}")
    return _DISABLED


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _import_tflite():
    global has_tflite_runtime
    try:
        import tflite_runtime.interpreter as tflite
        has_tflite_runtime = True
        return tflite
    except ImportError:
        pass
    try:
        import tensorflow.lite as tflite
        has_tflite_runtime = True
        return tflite
    except ImportError:
        has_tflite_runtime = False
        print("Prediction by model disabled: tensorflow or tflite-runtime package missing")
        return None


def _init_interpreter(tflite):
    global interpreter
    try:
        print(f"Selected model file: {model_path}")
        interpreter = tflite.Interpreter(model_path=model_path)
        interpreter.allocate_tensors()
        return True
    except Exception as e:
        print(f"Prediction by model disabled. Error: {e}")
        return False


def _detect_model_type():
    global interpreter
    try:
        input_details = interpreter.get_input_details()
        dummy = np.zeros(input_details[0]["shape"], dtype=np.float32)
        interpreter.set_tensor(input_details[0]["index"], dummy)
        interpreter.invoke()
        output = interpreter.get_tensor(interpreter.get_output_details()[0]["index"])
        num_classes = len(output[0])
        if num_classes == _MODEL_CLASSES_CONT:
            print("Prediction by model enabled. Model type: ana-cont")
        elif num_classes == _MODEL_CLASSES_CLASS100:
            print("Prediction by model enabled. Model type: ana-class100")
        else:
            print(f"Model type not supported. Detected classes: {num_classes}")
            interpreter = None
    except Exception as e:
        print(f"Error during model type detection: {e}")
        interpreter = None
