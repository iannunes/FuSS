import torch
import torch.nn.functional as F
from torch import nn

from utils import initialize_weights

class _EncoderBlock(nn.Module):

    def __init__(self, in_channels, out_channels, dropout=False):

        super(_EncoderBlock, self).__init__()

        layers = [
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        ]

        if dropout:

            layers.append(nn.Dropout())

        layers.append(nn.MaxPool2d(kernel_size=2, stride=2))

        self.encode = nn.Sequential(*layers)

    def forward(self, x):

        return self.encode(x)


class _DecoderBlock(nn.Module):

    def __init__(self, in_channels, middle_channels, out_channels):

        super(_DecoderBlock, self).__init__()

        self.decode = nn.Sequential(
            nn.Dropout2d(),
            nn.Conv2d(in_channels, middle_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(middle_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(middle_channels, middle_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(middle_channels),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(middle_channels, out_channels, kernel_size=2, stride=2, padding=0, output_padding=0)
        )

    def forward(self, x):

        return self.decode(x)


class UNet(nn.Module):

    def __init__(self, input_channels, num_classes, hidden_classes=None):

        super(UNet, self).__init__()

        self.enc1 = _EncoderBlock(input_channels, 64)
        self.enc2 = _EncoderBlock(64, 128)
        self.enc3 = _EncoderBlock(128, 256)
        self.enc4 = _EncoderBlock(256, 512, dropout=True)

        self.center = _DecoderBlock(512, 1024, 512)

        self.dec4 = _DecoderBlock(1024, 512, 256)
        self.dec3 = _DecoderBlock(512, 256, 128)
        self.dec2 = _DecoderBlock(256, 128, 64)

        self.dec1 = nn.Sequential(
            nn.Dropout2d(),
            nn.Conv2d(128, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
        )

        if hidden_classes is None:
            self.final = nn.Conv2d(64, num_classes, kernel_size=1)
        else:
            self.final = nn.Conv2d(64, num_classes - len(hidden_classes), kernel_size=1)

        initialize_weights(self)

    def forward(self, x, feat=False):

        enc1 = self.enc1(x)
#         print('enc1', enc1.size())
        enc2 = self.enc2(enc1)
#         print('enc2', enc2.size())
        enc3 = self.enc3(enc2)
#         print('enc3', enc3.size())
        enc4 = self.enc4(enc3)
#         print('enc4', enc4.size())

        center = self.center(enc4)
#         print('center', center.size())

        dec4 = self.dec4(torch.cat([center, F.interpolate(enc4, center.size()[2:], mode='bilinear')], 1))
#         print('dec4', dec4.size())
        dec3 = self.dec3(torch.cat([dec4, F.interpolate(enc3, dec4.size()[2:], mode='bilinear')], 1))
#         print('dec3', dec3.size())
        dec2 = self.dec2(torch.cat([dec3, F.interpolate(enc2, dec3.size()[2:], mode='bilinear')], 1))
#         print('dec2', dec2.size())
        dec1 = self.dec1(torch.cat([dec2, F.interpolate(enc1, dec2.size()[2:], mode='bilinear')], 1))
#         print('dec1', dec1.size())

        final = self.final(dec1)
#         print('final', final.size())

        if feat:
            return (F.interpolate(final, x.size()[2:], mode='bilinear'),
                    dec1,
                    F.interpolate(dec2, x.size()[2:], mode='bilinear'),
                    F.interpolate(dec3, x.size()[2:], mode='bilinear'),
                    F.interpolate(dec4, x.size()[2:], mode='bilinear'))
        else:
            return F.interpolate(final, x.size()[2:], mode='bilinear')
        