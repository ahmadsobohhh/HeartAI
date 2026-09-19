"""Use the published transform definitions directly, without custom CT windows."""
from monai.bundle import ConfigParser

from heartai.assets import BUNDLE, verify_asset


def inference_config(device="cpu"):
    config = BUNDLE / "configs/inference.json"
    verify_asset(config)
    parser = ConfigParser()
    parser.read_config(str(config))
    parser["displayable_configs#highres"] = False
    parser["device"] = device
    # Accumulate on CPU to avoid allocating a full 105-channel volume on GPU.
    parser["inferer#device"] = "cpu"
    parser["inferer#sw_device"] = device
    parser["inferer#progress"] = True
    # Save ourselves after verifying the restored grid and copying NIfTI forms.
    parser["postprocessing#transforms"] = parser["postprocessing#transforms"][:-1]
    return parser
