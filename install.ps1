$run_mode = $args[0]

pipenv install
pipenv install --dev
pipenv run pyinstaller --noconsole -F --icon=favicon.ico main.py

$appdata_path = [Environment]::GetFolderPath('ApplicationData')
$install_path = "$appdata_path\GameSaveManager"

if ($null -eq $run_mode -or $run_mode.ToLower() -eq "install" -or $run_mode.ToLower() -eq "") {
    Write-Output "Installing..."
    New-Item -Path $appdata_path -Name "GameSaveManager" -ItemType "directory" -ErrorAction SilentlyContinue
    Copy-Item ".\dist\main.exe" -destination $install_path
    Copy-Item ".\app_save_path_definitions.json" -destination $install_path
    Copy-Item ".\sample-config.json" -destination "$install_path\config.json"
}
elseif ($run_mode.ToLower() -eq "update") {
    Write-Output "Updating..."
    Copy-Item ".\dist\main.exe" -destination $install_path
    Copy-Item ".\app_save_path_definitions.json" -destination $install_path
}

try {
    $action = New-ScheduledTaskAction -Execute "$install_path\main.exe" -WorkingDirectory $install_path -ErrorAction Stop
    $trigger = New-ScheduledTaskTrigger -Daily -At 12am #([datetime]::Today) #-RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 1)
    $task = Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "GameSaveManager" -Description "Backs up game saves" -ErrorAction Stop
    $task.Triggers.Repetition.Duration = "P1D"
    $task.Triggers.Repetition.Interval = "PT1H"
    $task | Set-ScheduledTask
}
catch {
    Write-Output "Scheduled Task Already Exists. Skipping..."
}

Write-Output "Completed Install/Update"