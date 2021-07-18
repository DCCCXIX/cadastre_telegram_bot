# #!/usr/bin/env python

import logging

import numpy as np
import timm
import torch
from albumentations import Compose
from albumentations.pytorch import ToTensorV2
from PIL import Image
from torch import nn

# from flask import Flask, redirect, render_template, request, url_for

# app = Flask(__name__)


# @app.route("/")
# def main_form():
#     return render_template("main_form.html")


# @app.route("/", methods=["POST"])
# def proccess_request():
#     return result


# if __name__ == "__main__":
#     app.run(debug=True, port=int(os.environ.get("PORT", 5000)))


class EnClassifier(nn.Module):
    def __init__(self, model_arch, n_class, pretrained=True):
        super().__init__()
        self.model = timm.create_model(model_arch, pretrained=pretrained)
        n_features = self.model.classifier.in_features
        self.model.classifier = nn.Linear(n_features, 4096)
        self.classifier1 = nn.Linear(4096, n_class)
        self.classifier2 = nn.Linear(4096, n_class)
        self.classifier3 = nn.Linear(4096, n_class)
        self.classifier4 = nn.Linear(4096, n_class)
        self.classifier5 = nn.Linear(4096, n_class)

    def forward(self, x):
        x = self.model(x)
        x1 = self.classifier1(x)
        x2 = self.classifier2(x)
        x3 = self.classifier3(x)
        x4 = self.classifier4(x)
        x5 = self.classifier5(x)
        output = torch.cat((x1, x2, x3, x4, x5), dim=-1)
        output = torch.reshape(output, (output.size()[0], 5, 10))

        return output


class Model_Handler:
    def __init__(self):
        self.device = self.set_device()
        self.model = self.get_model()

    def set_device(self):
        if torch.cuda.is_available():
            device = torch.device("cuda:0")
            logging.info(f"Running on {torch.cuda.get_device_name()}")
        else:
            device = torch.device("cpu")
            logging.info("Running on a CPU")

        return device

    def get_model(self):
        model = EnClassifier("tf_efficientnet_b0_ns", 10).to(self.device)
        model.load_state_dict(torch.load("best.pth"))
        model.eval()

        return model

    def preproccess(self, image):
        transforms = Compose(
            [
                ToTensorV2(p=1.0),
            ],
            p=1.0,
        )

        image = Image.open(image)
        image = np.array(image)

        if image.shape[-1] == 4:  # removing alpha channel
            image = image[..., :3]

        image = np.rollaxis(image, -1, 0)[0]  # taking the first channel only
        # image > 0 = 255.0 works well on its own with png
        # this is temporart for testing w/ telegram
        image[image > 50] = 255.0
        image[image < 50] = 0.0

        if len(image.shape) == 2:  # converting single channel image to 3 channel for efficientnet
            image = np.stack((image,) * 3, axis=-1)

        image = transforms(image=image)["image"]

        return image

    def predict(self, image):
        input = self.preproccess(image).float()
        outputs = self.model(input.unsqueeze(0).to(self.device))
        outputs_argmax = [torch.argmax(i).item() for i in outputs[0]]
        outputs = "".join([str(i) for i in outputs_argmax])
        return outputs


mh = Model_Handler()
