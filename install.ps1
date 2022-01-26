Write-Output "Installing..."

pipenv install
pipenv install --dev
pipenv run pyinstaller --noconsole -F --icon=favicon.ico main.py

$appdata_path = [Environment]::GetFolderPath('ApplicationData')
$install_path = "$appdata_path\GameSaveManager"

New-Item -Path $appdata_path -Name "GameSaveManager" -ItemType "directory" -ErrorAction SilentlyContinue
Copy-Item ".\dist\main.exe" -destination $install_path
Copy-Item ".\app_save_path_definitions.json" -destination $install_path
Copy-Item ".\sample-config.json" -destination "$install_path\config.json"


$action = New-ScheduledTaskAction -Execute "$install_path\main.exe" -WorkingDirectory $install_path
$trigger = New-ScheduledTaskTrigger -Once -At ([datetime]::Today) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 1)
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "GameSaveManager" -Description "Backs up game saves"

Write-Output "Completed Install"