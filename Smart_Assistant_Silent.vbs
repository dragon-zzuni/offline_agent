Set WshShell = CreateObject("WScript.Shell")
' 현재 스크립트의 디렉토리 경로 가져오기
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' BAT 파일을 숨김 모드로 실행 (콘솔 창 없음)
WshShell.Run """" & scriptDir & "\Smart_Assistant.bat""", 0, False

' 0 = 창 숨김
' False = 스크립트가 완료될 때까지 기다리지 않음
