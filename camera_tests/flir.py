import PySpin
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np

class CameraStream:
    def __init__(self):
        self.system = PySpin.System.GetInstance()
        self.cam_list = self.system.GetCameras()
        print(self.cam_list)
        self.cam = self.cam_list[1]
        self.cam.Init()

        # optional: shrink resolution for smoother preview
        # nodemap = self.cam.GetNodeMap()
        # PySpin.CIntegerPtr(nodemap.GetNode("Width")).SetValue(640)
        # PySpin.CIntegerPtr(nodemap.GetNode("Height")).SetValue(480)

        self.cam.BeginAcquisition()

        self.root = tk.Tk()
        self.root.title("FLIR Camera Stream")
        self.label = tk.Label(self.root)
        self.label.pack()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.update()
        self.root.mainloop()

    def update(self):
        try:
            image = self.cam.GetNextImage(1000)
            if not image.IsIncomplete():
                data = image.GetNDArray()
                # mono sensor — convert to RGB for PIL
                if len(data.shape) == 2:
                    pil_img = Image.fromarray(data, mode='L')
                else:
                    pil_img = Image.fromarray(data)
                # resize for display
                pil_img = pil_img.resize((800, 600), Image.NEAREST)
                self.tk_img = ImageTk.PhotoImage(pil_img)
                self.label.config(image=self.tk_img)
            image.Release()
        except PySpin.SpinnakerException:
            pass
        self.root.after(30, self.update)

    def close(self):
        self.cam.EndAcquisition()
        self.cam.DeInit()
        del self.cam
        self.cam_list.Clear()
        self.system.ReleaseInstance()
        self.root.destroy()

if __name__ == "__main__":
    CameraStream()