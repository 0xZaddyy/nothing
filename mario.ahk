#Requires AutoHotkey v2.0

^m::  ; Ctrl+M
{
  styleToRemove := 0x00C00000 | 0x00040000 | 0x00800000  ; Remove title bar, thick frame, dialog frame
  MouseGetPos(,, &winID)

  if winID
  {
    WinSetStyle(-styleToRemove, winID)

    screenWidth := SysGet(78)
    screenHeight := SysGet(79)

    width := Round(screenWidth * 0.7335)          
    height := Round(width * 3 / 4) - 30              ; 4:3 ratio
    x := 0
    y := 135

    DllCall("SetWindowPos"
      , "Ptr", winID
      , "Ptr", 0
      , "Int", x
      , "Int", y
      , "Int", width
      , "Int", height
      , "UInt", 0x0040)  ; SWP_NOZORDER

    MsgBox "Window sized and positioned!"
  }
  else
  {
    MsgBox "No window found under mouse."
  }
}

^h::  ; Ctrl+H to hide taskbar
{
  DetectHiddenWindows True
  taskbar := WinGetID("ahk_class Shell_TrayWnd")
  WinHide("ahk_id " taskbar)
}

;^s::  ; Ctrl+S to show taskbar
;{
;  DetectHiddenWindows True
;  taskbar := WinGetID("ahk_class Shell_TrayWnd")
;  WinShow("ahk_id " taskbar)
;}