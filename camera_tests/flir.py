import PySpin

system = PySpin.System.GetInstance()
cam_list = system.GetCameras()
cam = cam_list[0]
cam.Init()
cam.BeginAcquisition()

image = cam.GetNextImage()
print(f"{image.GetWidth()}x{image.GetHeight()}")
image.Release()

cam.EndAcquisition()
cam.DeInit()
del cam
cam_list.Clear()
system.ReleaseInstance()