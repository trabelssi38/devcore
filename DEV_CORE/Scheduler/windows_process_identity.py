"""Read-only Windows process identity, using one process handle per snapshot."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path


def process_identity(pid):
    if os.name != 'nt':
        raise RuntimeError('Windows process identity required')
    if type(pid) is not int or not 1 <= pid < 2**32:
        raise ValueError('Invalid process PID')
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    api.GetProcessTimes.restype = wintypes.BOOL
    api.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
        wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    api.QueryFullProcessImageNameW.restype = wintypes.BOOL
    handle = api.OpenProcess(0x1000 | 0x100000, False, pid)  # QUERY_LIMITED | SYNCHRONIZE
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not api.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
            raise ctypes.WinError(ctypes.get_last_error())
        size = wintypes.DWORD(32768)
        image = ctypes.create_unicode_buffer(size.value)
        if not api.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        if api.WaitForSingleObject(handle, 0) != 258:  # WAIT_TIMEOUT means not exited.
            raise OSError('Process no longer alive or liveness unavailable')
        creation = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        return {'creation_100ns': creation, 'image': os.path.normcase(str(Path(image.value).resolve()))}
    finally:
        api.CloseHandle(handle)
