import torch

from heartai.assets import BUNDLE, verify_asset


def load_model(parser, device):
    checkpoint = BUNDLE / "models/model_lowres.pt"
    verify_asset(checkpoint)
    network = parser.get_parsed_content("network_def").to(device)
    weights = torch.load(checkpoint, map_location="cpu", weights_only=True)
    network.load_state_dict(weights, strict=True)
    network.eval()
    network.requires_grad_(False)
    return network
