"""Stream ONLY cam1 — use its default pixel format, don't force Mono8."""

import time
import tkinter as tk

import cv2
import numpy as np
from PIL import Image, ImageTk

import PySpin

system = PySpin.System.GetInstance()
cam_list = system.GetCameras()
print(f'{cam_list.GetSize()} cameras')

cam = cam_list[1]
cam.Init()

nm = cam.GetTLDeviceNodeMap()
sn = PySpin.CStringPtr(nm.GetNode('DeviceSerialNumber')).GetValue()
model = PySpin.CStringPtr(nm.GetNode('DeviceModelName')).GetValue()
print(f'{model}  S/N {sn}')

nodemap = cam.GetNodeMap()

# DON'T set pixel format — just read what it defaults to
pf = PySpin.CEnumerationPtr(nodemap.GetNode('PixelFormat'))
default_fmt = pf.GetCurrentEntry().GetSymbolic()
print(f'default pixel format: {default_fmt}')

# list all available formats
print('available formats:')
entries = pf.GetEntries()
for e in entries:
    e = PySpin.CEnumEntryPtr(e)
    if PySpin.IsAvailable(e) and PySpin.IsReadable(e):
        print(f'  {e.GetSymbolic()}')

# lower frame rate
try:
    node_en = PySpin.CBooleanPtr(nodemap.GetNode('AcquisitionFrameRateEnable'))
    if PySpin.IsAvailable(node_en) and PySpin.IsWritable(node_en):
        node_en.SetValue(True)
    node_fr = PySpin.CFloatPtr(nodemap.GetNode('AcquisitionFrameRate'))
    if PySpin.IsAvailable(node_fr) and PySpin.IsWritable(node_fr):
        node_fr.SetValue(min(15, node_fr.GetMax()))
        print(f'frame rate: {node_fr.GetValue():.1f}')
except PySpin.SpinnakerException as e:
    print(f'frame rate: {e}')

# stream buffers
s_nodemap = cam.GetTLStreamNodeMap()
try:
    handling = PySpin.CEnumerationPtr(
        s_nodemap.GetNode('StreamBufferHandlingMode'))
    newest = handling.GetEntryByName('NewestOnly')
    if PySpin.IsAvailable(newest):
        handling.SetIntValue(newest.GetValue())
except Exception:
    pass

cam.BeginAcquisition()
print('acquiring...')

root = tk.Tk()
root.title(f'cam1 solo — {model}')
lbl = tk.Label(root, background='#222')
lbl.pack()
sv = tk.StringVar(value='...')
tk.Label(root, textvariable=sv).pack()

n_frames = [0]
t0 = [time.perf_counter()]
fps = [0.0]

def poll():
    try:
        img = cam.GetNextImage(2000)
    except PySpin.SpinnakerException as e:
        sv.set(f'err: {e}')
        root.after(500, poll)
        return

    if img.IsIncomplete():
        sv.set(f'incomplete: status {img.GetImageStatus()}')
        img.Release()
        root.after(100, poll)
        return

    w, h = img.GetWidth(), img.GetHeight()
    bpp = img.GetBitsPerPixel()
    channels = max(1, bpp // 8)

    if channels == 1:
        arr = np.frombuffer(img.GetData(), dtype=np.uint8).reshape(h, w).copy()
        rgb = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
    elif 'Bayer' in default_fmt:
        arr = np.frombuffer(img.GetData(), dtype=np.uint8).reshape(h, w).copy()
        # try common Bayer conversions
        if 'RG' in default_fmt:
            rgb = cv2.cvtColor(arr, cv2.COLOR_BayerRG2RGB)
        elif 'GR' in default_fmt:
            rgb = cv2.cvtColor(arr, cv2.COLOR_BayerGR2RGB)
        elif 'GB' in default_fmt:
            rgb = cv2.cvtColor(arr, cv2.COLOR_BayerGB2RGB)
        else:
            rgb = cv2.cvtColor(arr, cv2.COLOR_BayerBG2RGB)
    else:
        # assume BGR or RGB 3-channel
        arr = np.frombuffer(img.GetData(), dtype=np.uint8
                            ).reshape(h, w, channels).copy()
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB) if channels == 3 else arr

    img.Release()

    n_frames[0] += 1
    now = time.perf_counter()
    if now - t0[0] >= 1.0:
        fps[0] = n_frames[0] / (now - t0[0])
        n_frames[0] = 0
        t0[0] = now

    new_h = max(1, int(h * 400 / w))
    small = cv2.resize(rgb, (400, new_h), interpolation=cv2.INTER_AREA)
    photo = ImageTk.PhotoImage(Image.fromarray(small))
    lbl.configure(image=photo)
    lbl.image = photo
    sv.set(f'{w}x{h} {default_fmt} {fps[0]:.1f} fps')

    root.after(1, poll)

root.after(1, poll)

def on_close():
    cam.EndAcquisition()
    cam.DeInit()
    del cam
    cam_list.Clear()
    system.ReleaseInstance()
    root.destroy()

root.protocol('WM_DELETE_WINDOW', on_close)
root.mainloop()