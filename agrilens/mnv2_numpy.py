"""Pure-NumPy MobileNetV2 (torchvision-compatible) forward pass.

No torch, no TFLite, no ONNX runtime — just numpy + the exported .npz weights.
This is the only dependency the phone-side code needs besides Pillow.
"""
import numpy as np

# t, c, n, s  (expand_ratio, out_channels, repeats, stride-of-first-repeat)
INVERTED_RESIDUAL_SETTING = [
    [1, 16, 1, 1],
    [6, 24, 2, 2],
    [6, 32, 3, 2],
    [6, 64, 4, 2],
    [6, 96, 3, 1],
    [6, 160, 3, 2],
    [6, 320, 1, 1],
]


def im2col(x, kh, kw, stride, pad):
    """x: (C, H, W) -> cols: (C*kh*kw, out_h*out_w), plus (out_h, out_w)."""
    c, h, w = x.shape
    if pad > 0:
        xp = np.zeros((c, h + 2 * pad, w + 2 * pad), dtype=x.dtype)
        xp[:, pad:pad + h, pad:pad + w] = x
    else:
        xp = x
    hp, wp = xp.shape[1], xp.shape[2]
    out_h = (hp - kh) // stride + 1
    out_w = (wp - kw) // stride + 1

    # Build strided view: (C, kh, kw, out_h, out_w)
    s0, s1, s2 = xp.strides
    shape = (c, kh, kw, out_h, out_w)
    strides = (s0, s1, s2, s1 * stride, s2 * stride)
    windows = np.lib.stride_tricks.as_strided(xp, shape=shape, strides=strides)
    cols = windows.reshape(c * kh * kw, out_h * out_w)
    return cols, out_h, out_w


def conv2d(x, weight, stride=1, pad=0, groups=1, bias=None):
    """x: (Cin,H,W), weight: (Cout,Cin/groups,kh,kw) -> (Cout,out_h,out_w)."""
    cin, h, w = x.shape
    cout, cin_g, kh, kw = weight.shape

    if groups == 1:
        cols, out_h, out_w = im2col(x, kh, kw, stride, pad)
        wmat = weight.reshape(cout, cin_g * kh * kw)
        out = wmat @ cols  # (Cout, out_h*out_w)
        out = out.reshape(cout, out_h, out_w)
    elif groups == cin and cin_g == 1:
        # depthwise: one filter per input channel
        if pad > 0:
            xp = np.zeros((cin, h + 2 * pad, w + 2 * pad), dtype=x.dtype)
            xp[:, pad:pad + h, pad:pad + w] = x
        else:
            xp = x
        hp, wp = xp.shape[1], xp.shape[2]
        out_h = (hp - kh) // stride + 1
        out_w = (wp - kw) // stride + 1
        s0, s1, s2 = xp.strides
        shape = (cin, kh, kw, out_h, out_w)
        strides = (s0, s1, s2, s1 * stride, s2 * stride)
        windows = np.lib.stride_tricks.as_strided(xp, shape=shape, strides=strides)
        # windows: (cin, kh, kw, out_h, out_w); weight: (cin,1,kh,kw) -> (cin,kh,kw)
        wflat = weight.reshape(cin, kh, kw)
        out = np.einsum("cijhw,cij->chw", windows, wflat, optimize=True)
    else:
        raise NotImplementedError("only groups=1 or depthwise supported")

    if bias is not None:
        out = out + bias.reshape(-1, 1, 1)
    return out


def bn_fold(weight, bias, running_mean, running_var, eps=1e-5):
    """Fold BatchNorm (inference) into per-channel scale + shift."""
    std = np.sqrt(running_var + eps)
    scale = weight / std
    shift = bias - running_mean * scale
    return scale, shift


def apply_bn(x, scale, shift):
    return x * scale.reshape(-1, 1, 1) + shift.reshape(-1, 1, 1)


def relu6(x):
    return np.clip(x, 0, 6)


class ConvBNAct:
    """Conv2dNormActivation: conv -> BN -> (optional ReLU6)."""

    def __init__(self, w, stride, pad, groups, bn_w, bn_b, bn_rm, bn_rv, act=True):
        self.w = w
        self.stride = stride
        self.pad = pad
        self.groups = groups
        self.scale, self.shift = bn_fold(bn_w, bn_b, bn_rm, bn_rv)
        self.act = act

    def __call__(self, x):
        x = conv2d(x, self.w, stride=self.stride, pad=self.pad, groups=self.groups)
        x = apply_bn(x, self.scale, self.shift)
        if self.act:
            x = relu6(x)
        return x


class InvertedResidual:
    def __init__(self, params, prefix, inp, oup, stride, expand_ratio):
        self.stride = stride
        self.use_res_connect = stride == 1 and inp == oup
        hidden_dim = int(round(inp * expand_ratio))
        layers = []
        idx = 0
        if expand_ratio != 1:
            w = params[f"{prefix}.conv.{idx}.0.weight"]
            bn = (
                params[f"{prefix}.conv.{idx}.1.weight"],
                params[f"{prefix}.conv.{idx}.1.bias"],
                params[f"{prefix}.conv.{idx}.1.running_mean"],
                params[f"{prefix}.conv.{idx}.1.running_var"],
            )
            layers.append(ConvBNAct(w, 1, 0, 1, *bn, act=True))  # pw expand, k=1,pad=0
            idx += 1
        # dw
        w = params[f"{prefix}.conv.{idx}.0.weight"]
        bn = (
            params[f"{prefix}.conv.{idx}.1.weight"],
            params[f"{prefix}.conv.{idx}.1.bias"],
            params[f"{prefix}.conv.{idx}.1.running_mean"],
            params[f"{prefix}.conv.{idx}.1.running_var"],
        )
        layers.append(ConvBNAct(w, stride, 1, hidden_dim, *bn, act=True))  # dw k=3,pad=1,groups=hidden_dim
        idx += 1
        # pw-linear (conv then separate BN, no activation)
        w = params[f"{prefix}.conv.{idx}.weight"]
        idx += 1
        bn = (
            params[f"{prefix}.conv.{idx}.weight"],
            params[f"{prefix}.conv.{idx}.bias"],
            params[f"{prefix}.conv.{idx}.running_mean"],
            params[f"{prefix}.conv.{idx}.running_var"],
        )
        layers.append(ConvBNAct(w, 1, 0, 1, *bn, act=False))  # pw-linear k=1,pad=0, no relu
        self.layers = layers

    def __call__(self, x):
        out = x
        for layer in self.layers:
            out = layer(out)
        if self.use_res_connect:
            out = x + out
        return out


class MobileNetV2Numpy:
    def __init__(self, npz_path):
        raw = np.load(npz_path)
        params = {k: raw[k] for k in raw.files}

        # stem: features.0 = Conv2dNormActivation(3,32,k=3,stride=2,pad=1)
        w = params["features.0.0.weight"]
        bn = (
            params["features.0.1.weight"],
            params["features.0.1.bias"],
            params["features.0.1.running_mean"],
            params["features.0.1.running_var"],
        )
        self.stem = ConvBNAct(w, 2, 1, 1, *bn, act=True)

        # 17 inverted residual blocks, features.1 .. features.17
        blocks = []
        input_channel = 32
        block_idx = 1
        for t, c, n, s in INVERTED_RESIDUAL_SETTING:
            output_channel = c  # width_mult=1.0, round_nearest already baked into checkpoint shapes
            for i in range(n):
                stride = s if i == 0 else 1
                blocks.append(
                    InvertedResidual(params, f"features.{block_idx}", input_channel, output_channel, stride, t)
                )
                input_channel = output_channel
                block_idx += 1
        self.blocks = blocks

        # final 1x1 conv: features.18
        w = params["features.18.0.weight"]
        bn = (
            params["features.18.1.weight"],
            params["features.18.1.bias"],
            params["features.18.1.running_mean"],
            params["features.18.1.running_var"],
        )
        self.head_conv = ConvBNAct(w, 1, 0, 1, *bn, act=True)

        # classifier: this checkpoint's head is classifier = Sequential(Dropout,
        # Sequential(Dropout, Linear)) -- both outer and inner Dropout are keyless
        # and no-ops at inference, so the only params are under "classifier.1.1.*".
        self.fc_w = params["classifier.1.1.weight"]  # (num_classes, 1280)
        self.fc_b = params["classifier.1.1.bias"]

    def __call__(self, x):
        """x: (3,224,224) float32, already normalized. Returns logits (num_classes,)."""
        x = self.stem(x)
        for block in self.blocks:
            x = block(x)
        x = self.head_conv(x)
        # global average pool
        x = x.mean(axis=(1, 2))  # (1280,)
        logits = self.fc_w @ x + self.fc_b
        return logits
